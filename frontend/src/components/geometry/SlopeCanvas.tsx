'use client';

import { useEffect, useRef } from 'react';
import { useAnalysisStore } from '@/store/analysisStore';
import type { Circle, Slice, SoilLayer } from '@/lib/types';

const COLORS = ['#d9c27a', '#b99555', '#91734d', '#6f6048', '#4f493d'];

function plateaus(H: number, L: number) {
  return {
    upstream: Math.max(1.5 * L, 2.5 * H),
    downstream: Math.max(2.5 * L, 4.0 * H),
  };
}

function terrainY(x: number, H: number, L: number, upstream: number) {
  const toe = upstream + L;
  if (x <= upstream) return H;
  if (x >= toe) return 0;
  return H * (1 - (x - upstream) / L);
}

function layerInterfaces(H: number, layers: SoilLayer[]) {
  const values: number[] = [];
  let z = H;
  for (const layer of layers.slice(0, -1)) {
    z -= layer.thickness ?? 0;
    values.push(z);
  }
  return values;
}

function drawLabel(ctx: CanvasRenderingContext2D, text: string, x: number, y: number) {
  ctx.save();
  ctx.font = '600 12px system-ui, sans-serif';
  const w = ctx.measureText(text).width;
  ctx.fillStyle = 'rgba(255, 255, 255, 0.88)';
  ctx.fillRect(x - 6, y - 17, w + 12, 22);
  ctx.fillStyle = '#334155';
  ctx.fillText(text, x, y);
  ctx.restore();
}

export default function SlopeCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { layers, waterTable, slopeHeight, slopeLength, result, criticalResult } =
    useAnalysisStore((s) => ({
      layers: s.layers,
      waterTable: s.waterTable,
      slopeHeight: s.slopeHeight,
      slopeLength: s.slopeLength,
      result: s.result,
      criticalResult: s.criticalResult,
    }));

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = canvas.width;
    const Hpx = canvas.height;
    const H = Math.max(slopeHeight, 0.1);
    const L = Math.max(slopeLength, 0.1);
    const { upstream, downstream } = plateaus(H, L);
    const xTotal = upstream + L + downstream;
    const solvedCircle: Circle | undefined = criticalResult?.critical_circle ?? result?.circle;
    const previewCircle: Circle = {
      cx: upstream + L * 0.32,
      cy: H * 1.15,
      radius: Math.max(H * 1.35, L * 0.85),
    };
    const circle: Circle = solvedCircle ?? previewCircle;

    const terrain = [
      [0, H],
      [upstream, H],
      [upstream + L, 0],
      [xTotal, 0],
    ] as Array<[number, number]>;

    const depth = Math.max(H * 0.35, 3);
    const xMin = 0;
    const xMax = xTotal;
    let yMin = -depth;
    let yMax = H + Math.max(H * 0.22, 2);

    yMin = Math.min(yMin, circle.cy - circle.radius * 0.12);
    yMax = Math.max(yMax, circle.cy + circle.radius * 0.12);

    const pad = { left: 54, right: 34, top: 34, bottom: 50 };
    const sx = (x: number) => pad.left + ((x - xMin) / (xMax - xMin)) * (W - pad.left - pad.right);
    const sy = (y: number) => pad.top + ((yMax - y) / (yMax - yMin)) * (Hpx - pad.top - pad.bottom);

    ctx.clearRect(0, 0, W, Hpx);
    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(0, 0, W, Hpx);

    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 8; i += 1) {
      const x = pad.left + (i / 8) * (W - pad.left - pad.right);
      ctx.beginPath();
      ctx.moveTo(x, pad.top);
      ctx.lineTo(x, Hpx - pad.bottom);
      ctx.stroke();
    }
    for (let i = 0; i <= 6; i += 1) {
      const y = pad.top + (i / 6) * (Hpx - pad.top - pad.bottom);
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(W - pad.right, y);
      ctx.stroke();
    }

    const xs = Array.from({ length: 280 }, (_, i) => (i / 279) * xTotal);
    const interfaces = layerInterfaces(H, layers);
    const bottoms = [...interfaces, yMin];

    layers.forEach((layer, i) => {
      const bottom = bottoms[i] ?? yMin;
      const topLimit = i === 0 ? H : interfaces[i - 1] ?? H;
      ctx.beginPath();
      xs.forEach((x, idx) => {
        const top = Math.min(terrainY(x, H, L, upstream), topLimit);
        const px = sx(x);
        const py = sy(Math.max(bottom, top));
        if (idx === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      [...xs].reverse().forEach((x) => ctx.lineTo(sx(x), sy(bottom)));
      ctx.closePath();
      ctx.fillStyle = COLORS[i % COLORS.length];
      ctx.globalAlpha = 0.78;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.strokeStyle = 'rgba(92, 70, 35, 0.35)';
      ctx.stroke();
      drawLabel(ctx, layer.name, sx(upstream + L + downstream * 0.42), sy((topLimit + bottom) / 2));
    });

    ctx.beginPath();
    terrain.forEach(([x, y], idx) => {
      if (idx === 0) ctx.moveTo(sx(x), sy(y));
      else ctx.lineTo(sx(x), sy(y));
    });
    ctx.strokeStyle = '#172033';
    ctx.lineWidth = 3;
    ctx.stroke();

    if (waterTable.elevation > yMin && waterTable.elevation < yMax) {
      ctx.strokeStyle = '#1478a8';
      ctx.setLineDash([7, 5]);
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(sx(0), sy(waterTable.elevation));
      ctx.lineTo(sx(xTotal), sy(waterTable.elevation));
      ctx.stroke();
      ctx.setLineDash([]);
      drawLabel(ctx, 'Nappe', sx(xTotal) - 84, sy(waterTable.elevation) - 8);
    }

    const slices: Slice[] = result?.slices ?? [];
    if (slices.length > 0) {
      ctx.strokeStyle = 'rgba(51, 65, 85, 0.22)';
      ctx.lineWidth = 1;
      slices.forEach((slc) => {
        ctx.beginPath();
        ctx.moveTo(sx(slc.x_left), sy(slc.y_base));
        ctx.lineTo(sx(slc.x_left), sy(slc.y_top));
        ctx.stroke();
      });
    }

    ctx.save();
    ctx.beginPath();
    ctx.rect(pad.left, pad.top, W - pad.left - pad.right, Hpx - pad.top - pad.bottom);
    ctx.clip();
    ctx.strokeStyle = solvedCircle ? '#b08900' : 'rgba(176, 137, 0, 0.55)';
    ctx.lineWidth = solvedCircle ? 4 : 3;
    if (!solvedCircle) ctx.setLineDash([12, 8]);
    ctx.beginPath();
    for (let i = 0; i <= 360; i += 1) {
      const t = (i / 360) * Math.PI * 2;
      const x = circle.cx + circle.radius * Math.cos(t);
      const y = circle.cy + circle.radius * Math.sin(t);
      if (i === 0) ctx.moveTo(sx(x), sy(y));
      else ctx.lineTo(sx(x), sy(y));
    }
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
    if (circle.cx >= xMin && circle.cx <= xMax && circle.cy >= yMin && circle.cy <= yMax) {
      ctx.fillStyle = solvedCircle ? '#b08900' : '#c7a33a';
      ctx.beginPath();
      ctx.arc(sx(circle.cx), sy(circle.cy), 4, 0, Math.PI * 2);
      ctx.fill();
    }
    drawLabel(
      ctx,
      solvedCircle ? 'Cercle critique calculé' : 'Surface indicative avant calcul',
      sx(Math.max(upstream * 0.7, 2)),
      sy(H + Math.max(1, H * 0.1)),
    );

    drawLabel(ctx, `H = ${H.toFixed(2)} m`, sx(upstream * 0.16), sy(H / 2));
    drawLabel(ctx, `L = ${L.toFixed(2)} m`, sx(upstream + L * 0.45), sy(-depth * 0.58));
  }, [layers, waterTable, slopeHeight, slopeLength, result, criticalResult]);

  return (
    <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div className="flex items-center gap-4 text-xs font-semibold text-slate-600">
          <span className="inline-flex items-center gap-2"><i className="h-2 w-5 rounded bg-[#d9c27a]" /> Sol</span>
          <span className="inline-flex items-center gap-2"><i className="h-0.5 w-5 bg-[#1478a8]" /> Nappe</span>
          <span className="inline-flex items-center gap-2"><i className="h-0.5 w-5 bg-[#b08900]" /> Surface de rupture</span>
        </div>
      </div>
      <canvas
        ref={canvasRef}
        width={1200}
        height={760}
        className="min-h-0 flex-1 w-full"
        aria-label="Profil du talus avec surface de rupture critique"
      />
    </section>
  );
}
