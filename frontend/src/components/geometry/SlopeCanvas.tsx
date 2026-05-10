'use client';

import { useEffect, useRef, useState } from 'react';
import type { PointerEvent, WheelEvent } from 'react';
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
    const t = isFinite(layer.thickness ?? 0) ? (layer.thickness ?? 0) : 0;
    z -= t;
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

function slipArcPoints(
  circle: Circle,
  H: number,
  L: number,
  upstream: number,
) {
  const points: Array<[number, number]> = [];
  const toe = upstream + L;
  const xMin = Math.max(0, upstream - Math.max(L, H));
  const xMax = toe + Math.max(L, H);
  const yMin = -Math.max(H * 0.75, 5);
  const yMax = H + Math.max(H * 0.35, 3);
  for (let i = 0; i <= 720; i += 1) {
    const theta = (i / 720) * Math.PI * 2;
    const x = circle.cx + circle.radius * Math.cos(theta);
    const y = circle.cy + circle.radius * Math.sin(theta);
    const insideModel = x >= xMin && x <= xMax && y >= yMin && y <= yMax;
    const lowerArc = y <= circle.cy;
    const belowTerrain = y <= terrainY(x, H, L, upstream) + 0.02;
    if (insideModel && lowerArc && belowTerrain) {
      points.push([x, y]);
    }
  }
  return longestContinuousArc(points);
}

function longestContinuousArc(points: Array<[number, number]>) {
  if (points.length < 2) return points;
  const segments: Array<Array<[number, number]>> = [[points[0]]];
  for (let i = 1; i < points.length; i += 1) {
    const [x0, y0] = points[i - 1];
    const [x1, y1] = points[i];
    const gap = Math.hypot(x1 - x0, y1 - y0);
    const current = segments[segments.length - 1];
    if (gap > 2.0) segments.push([points[i]]);
    else current.push(points[i]);
  }
  return segments.reduce((best, segment) => (segment.length > best.length ? segment : best), segments[0]);
}

export default function SlopeCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dragRef = useRef<{ x: number; y: number } | null>(null);
  const viewRef = useRef({
    xSpan: 1,
    ySpan: 1,
    plotW: 1,
    plotH: 1,
  });
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [canvasSize, setCanvasSize] = useState({ width: 1200, height: 760 });
  const { layers, waterTable, slopeHeight, slopeLength, result, criticalResult } =
    useAnalysisStore((s) => ({
      layers: s.layers,
      waterTable: s.waterTable,
      slopeHeight: s.slopeHeight,
      slopeLength: s.slopeLength,
      result: s.result,
      criticalResult: s.criticalResult,
    }));
  const circleViewKey = criticalResult?.critical_circle
    ? `${criticalResult.critical_circle.cx}:${criticalResult.critical_circle.cy}:${criticalResult.critical_circle.radius}`
    : 'no-circle';

  useEffect(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, [circleViewKey, slopeHeight, slopeLength]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const observer = new ResizeObserver(([entry]) => {
      const width = Math.max(1, Math.round(entry.contentRect.width));
      const height = Math.max(1, Math.round(entry.contentRect.height));
      setCanvasSize((current) => (
        current.width === width && current.height === height ? current : { width, height }
      ));
    });

    observer.observe(canvas);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const W = canvasSize.width;
    const Hpx = canvasSize.height;
    const deviceW = Math.round(W * dpr);
    const deviceH = Math.round(Hpx * dpr);
    if (canvas.width !== deviceW || canvas.height !== deviceH) {
      canvas.width = deviceW;
      canvas.height = deviceH;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const H = isFinite(slopeHeight) && slopeHeight > 0 ? slopeHeight : 10;
    const L = isFinite(slopeLength) && slopeLength > 0 ? slopeLength : 15;
    const { upstream, downstream } = plateaus(H, L);
    const xTotal = upstream + L + downstream;
    const solvedCircle: Circle | undefined = criticalResult?.critical_circle ?? result?.circle;
    const circle: Circle | undefined = solvedCircle;

    const terrain = [
      [0, H],
      [upstream, H],
      [upstream + L, 0],
      [xTotal, 0],
    ] as Array<[number, number]>;

    const depth = Math.max(H * 0.35, 3);
    let baseXMin = 0;
    let baseXMax = xTotal;
    let baseYMin = -depth;
    let baseYMax = H + Math.max(H * 0.22, 2);

    if (circle) {
      const arc = slipArcPoints(circle, H, L, upstream);
      const focusX = [
        upstream - Math.max(L * 1.10, H * 2.0),
        upstream + L + Math.max(L * 1.10, H * 2.0),
      ];
      const focusY = [
        -Math.max(H * 0.90, 5),
        H + Math.max(H * 1.20, L * 0.25, 4),
      ];
      if (arc.length > 1) {
        const xsArc = arc.map(([x]) => x);
        const ysArc = arc.map(([, y]) => y);
        focusX.push(Math.min(...xsArc), Math.max(...xsArc));
        focusY.push(Math.min(...ysArc), Math.max(...ysArc));
      }
      if (circle.radius <= Math.max(4 * H, 2 * L)) {
        focusX.push(circle.cx - circle.radius * 0.35, circle.cx + circle.radius * 0.35);
        focusY.push(circle.cy - circle.radius * 0.35, circle.cy + circle.radius * 0.35);
      }
      const marginX = Math.max(L * 0.28, H * 0.6, 4);
      const marginY = Math.max(H * 0.25, 2);
      baseXMin = Math.max(0, Math.min(...focusX) - marginX);
      baseXMax = Math.min(xTotal, Math.max(...focusX) + marginX);
      baseYMin = Math.min(...focusY) - marginY;
      baseYMax = Math.max(...focusY) + marginY;
    }

    const visibleXSpan = Math.max(baseXMax - baseXMin, L + H * 2);
    const horizontalBreathing = Math.max(visibleXSpan * 0.10, H * 0.8, 3);
    baseXMin = Math.max(0, baseXMin - horizontalBreathing);
    baseXMax = Math.min(xTotal, baseXMax + horizontalBreathing);

    const pad = { left: 78, right: 64, top: 42, bottom: 56 };
    const plotW = W - pad.left - pad.right;
    const plotH = Hpx - pad.top - pad.bottom;
    const xCenter = (baseXMin + baseXMax) / 2 + pan.x;
    const yCenter = (baseYMin + baseYMax) / 2 + pan.y;
    const rawXSpan = (baseXMax - baseXMin) / zoom;
    const rawYSpan = (baseYMax - baseYMin) / zoom;
    const metresPerPixel = Math.max(rawXSpan / plotW, rawYSpan / plotH);
    const xSpan = metresPerPixel * plotW;
    const ySpan = metresPerPixel * plotH;
    const xMin = xCenter - xSpan / 2;
    const xMax = xCenter + xSpan / 2;
    const yMin = yCenter - ySpan / 2;
    const yMax = yCenter + ySpan / 2;

    viewRef.current = {
      xSpan,
      ySpan,
      plotW,
      plotH,
    };
    const sx = (x: number) => pad.left + ((x - xMin) / (xMax - xMin)) * plotW;
    const sy = (y: number) => pad.top + ((yMax - y) / (yMax - yMin)) * plotH;

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

    if (waterTable.elevation !== null && waterTable.elevation > yMin && waterTable.elevation < yMax) {
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

    if (circle) {
      const arc = slipArcPoints(circle, H, L, upstream);
      const slices: Slice[] = result?.slices ?? [];

      ctx.save();
      ctx.beginPath();
      ctx.rect(pad.left, pad.top, W - pad.left - pad.right, Hpx - pad.top - pad.bottom);
      ctx.clip();

      // --- 1. Fill the sliding mass (terrain surface → arc) ---
      if (arc.length >= 2) {
        const entry = arc[0];
        const exit_ = arc[arc.length - 1];
        ctx.beginPath();
        ctx.moveTo(sx(entry[0]), sy(entry[1]));
        const nSteps = 80;
        for (let i = 1; i <= nSteps; i++) {
          const xi = entry[0] + (i / nSteps) * (exit_[0] - entry[0]);
          ctx.lineTo(sx(xi), sy(terrainY(xi, H, L, upstream)));
        }
        for (let i = arc.length - 1; i >= 0; i--) {
          ctx.lineTo(sx(arc[i][0]), sy(arc[i][1]));
        }
        ctx.closePath();
        ctx.fillStyle = 'rgba(176, 137, 0, 0.10)';
        ctx.fill();
      }

      // --- 2. Slices: left wall + inclined arc base (base follows circle geometry) ---
      if (slices.length > 0) {
        ctx.strokeStyle = 'rgba(15, 23, 42, 0.28)';
        ctx.lineWidth = 1;
        slices.forEach((slc, i) => {
          const dxL = slc.x_left - circle.cx;
          const dxR = slc.x_right - circle.cx;
          const discL = circle.radius ** 2 - dxL ** 2;
          const discR = circle.radius ** 2 - dxR ** 2;
          if (discL < 0 || discR < 0) return;
          const yBL = circle.cy - Math.sqrt(discL); // arc y at left edge
          const yBR = circle.cy - Math.sqrt(discR); // arc y at right edge
          const yTL = terrainY(slc.x_left, H, L, upstream);
          const yTR = terrainY(slc.x_right, H, L, upstream);

          // Left vertical wall
          ctx.beginPath();
          ctx.moveTo(sx(slc.x_left), sy(yTL));
          ctx.lineTo(sx(slc.x_left), sy(yBL));
          ctx.stroke();

          // Inclined base following the arc
          ctx.beginPath();
          ctx.moveTo(sx(slc.x_left), sy(yBL));
          ctx.lineTo(sx(slc.x_right), sy(yBR));
          ctx.stroke();

          // Right wall only on the last slice (closes the diagram)
          if (i === slices.length - 1) {
            ctx.beginPath();
            ctx.moveTo(sx(slc.x_right), sy(yTR));
            ctx.lineTo(sx(slc.x_right), sy(yBR));
            ctx.stroke();
          }
        });
      }

      // --- 3. Full circle outline (dashed, light) ---
      const radiusPx = circle.radius / metresPerPixel;
      ctx.strokeStyle = 'rgba(176, 137, 0, 0.22)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([8, 8]);
      ctx.beginPath();
      ctx.arc(sx(circle.cx), sy(circle.cy), radiusPx, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);

      // --- 4. Critical arc (solid gold, bold) ---
      ctx.strokeStyle = '#b08900';
      ctx.lineWidth = 4;
      ctx.beginPath();
      arc.forEach(([x, y], idx) => {
        if (idx === 0) ctx.moveTo(sx(x), sy(y));
        else ctx.lineTo(sx(x), sy(y));
      });
      ctx.stroke();

      ctx.restore();

      // --- 5. Entry / exit dots + labels ---
      if (arc.length >= 2) {
        const epData: [number, number, string, number][] = [
          [arc[0][0], arc[0][1], 'Entrée', 12],
          [arc[arc.length - 1][0], arc[arc.length - 1][1], 'Sortie', -74],
        ];
        epData.forEach(([x, y, label, offsetX]) => {
          ctx.fillStyle = '#b08900';
          ctx.beginPath();
          ctx.arc(sx(x), sy(y), 5, 0, Math.PI * 2);
          ctx.fill();
          drawLabel(ctx, label, sx(x) + offsetX, sy(y) - 8);
        });
      }

      // --- 6. Circle centre dot ---
      if (circle.cx >= xMin && circle.cx <= xMax && circle.cy >= yMin && circle.cy <= yMax) {
        ctx.fillStyle = '#b08900';
        ctx.beginPath();
        ctx.arc(sx(circle.cx), sy(circle.cy), 4, 0, Math.PI * 2);
        ctx.fill();
      }

      const labelX = arc.length >= 2 ? Math.min(arc[0][0] + H * 0.35, upstream + L * 0.45) : upstream + L * 0.18;
      drawLabel(ctx, 'Surface de rupture critique', sx(labelX), sy(H + Math.max(0.8, H * 0.08)));
    }

    if (result?.fs && isFinite(result.fs)) {
      drawLabel(ctx, `FoS = ${result.fs.toFixed(3)}`, sx(upstream + L * 0.08), sy(H + Math.max(1.6, H * 0.18)));
    }

    drawLabel(ctx, `H = ${H.toFixed(2)} m`, sx(upstream * 0.16), sy(H / 2));
    drawLabel(ctx, `L = ${L.toFixed(2)} m`, sx(upstream + L * 0.45), sy(-depth * 0.58));
  }, [layers, waterTable, slopeHeight, slopeLength, result, criticalResult, zoom, pan, canvasSize]);

  const handleWheel = (event: WheelEvent<HTMLCanvasElement>) => {
    event.preventDefault();
    setZoom((current) => {
      const factor = event.deltaY < 0 ? 1.12 : 1 / 1.12;
      return Math.max(0.6, Math.min(5, current * factor));
    });
  };

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const handlePointerDown = (event: PointerEvent<HTMLCanvasElement>) => {
    dragRef.current = { x: event.clientX, y: event.clientY };
    setIsDragging(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: PointerEvent<HTMLCanvasElement>) => {
    if (!dragRef.current) return;
    const dy = event.clientY - dragRef.current.y;
    dragRef.current = { x: event.clientX, y: event.clientY };

    const { ySpan, plotH } = viewRef.current;
    setPan((current) => ({
      x: 0,
      y: current.y + (dy / plotH) * ySpan,
    }));
  };

  const stopDrag = (event: PointerEvent<HTMLCanvasElement>) => {
    dragRef.current = null;
    setIsDragging(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  return (
    <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div className="flex items-center gap-4 text-xs font-semibold text-slate-600">
          <span className="inline-flex items-center gap-2"><i className="h-2 w-5 rounded bg-[#d9c27a]" /> Sol</span>
          <span className="inline-flex items-center gap-2"><i className="h-0.5 w-5 bg-[#1478a8]" /> Nappe</span>
          <span className="inline-flex items-center gap-2"><i className="h-0.5 w-5 bg-[#b08900]" /> Surface de rupture</span>
        </div>
        <button
          type="button"
          onClick={resetView}
          className="h-8 rounded-lg border border-slate-300 bg-white px-3 text-xs font-black text-slate-700 transition hover:bg-slate-50"
        >
          Recentrer
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-hidden">
        <canvas
          ref={canvasRef}
          width={1200}
          height={760}
          onWheel={handleWheel}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={stopDrag}
          onPointerCancel={stopDrag}
          onDoubleClick={resetView}
          className={`h-full min-h-0 w-full touch-none select-none ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
          aria-label="Profil du talus avec surface de rupture critique"
        />
      </div>
    </section>
  );
}
