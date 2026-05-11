'use client';

import { useEffect, useState } from 'react';
import { useAnalysisStore } from '@/store/analysisStore';
import type { SoilLayer } from '@/lib/types';

type DraftLayer = SoilLayer & { mode: 'create' | 'edit' };

function emptyLayer(existingLayers: { id: number }[]): SoilLayer {
  const maxId = existingLayers.reduce((m, l) => Math.max(m, l.id), 0);
  const id = maxId + 1;
  return {
    id,
    name: `C${id}`,
    gamma: 20.0,
    cohesion: 10.0,
    phi_deg: 30.0,
    thickness: 2.0,
  };
}

function remainingThickness(layers: SoilLayer[], slopeHeight: number) {
  const used = layers.reduce((sum, layer) => sum + (layer.thickness ?? 0), 0);
  return Math.max(0, slopeHeight - used);
}

function finiteThicknessSum(layers: SoilLayer[]) {
  return layers.reduce((sum, layer) => sum + (layer.thickness ?? 0), 0);
}

function withBottomSubstratum(layers: SoilLayer[]) {
  if (layers.length === 0) return layers;
  return layers.map((layer, index) => (
    index === layers.length - 1
      ? { ...layer, thickness: null }
      : layer.thickness === null
        ? { ...layer, thickness: 2.0 }
        : layer
  ));
}

function renumberAutomaticLayerNames(layers: SoilLayer[]) {
  const allAutomatic = layers.every((layer) => /^C\d+$/.test(layer.name));
  if (!allAutomatic) return layers;
  return layers.map((layer, index) => ({ ...layer, name: `C${index + 1}` }));
}

function displayedThickness(layers: SoilLayer[], index: number, slopeHeight: number) {
  const previous = layers
    .slice(0, index)
    .reduce((sum, layer) => sum + (layer.thickness ?? 0), 0);
  const current = layers[index];
  if (current.thickness !== null) return current.thickness;
  return Math.max(0, slopeHeight - previous);
}

function parseDecimalInput(value: string) {
  const normalized = value.replace(',', '.').trim();
  if (normalized === '') return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function NumberInput({
  label,
  unit,
  value,
  min,
  max,
  required = true,
  disabled = false,
  onChange,
}: {
  label: string;
  unit: string;
  value: number | null;
  min?: number;
  max?: number;
  required?: boolean;
  step: number;
  disabled?: boolean;
  onChange: (value: number) => void;
}) {
  const [draftValue, setDraftValue] = useState(value === null ? '' : String(value));

  useEffect(() => {
    setDraftValue(value === null ? '' : String(value));
  }, [value]);

  const parsedDraft = parseDecimalInput(draftValue);
  const error = (() => {
    if (disabled) return null;
    if (draftValue.trim() === '') return required ? 'Valeur obligatoire.' : null;
    if (parsedDraft === null) return 'Valeur numérique invalide.';
    if (min !== undefined && parsedDraft < min) return `Valeur minimale : ${min}.`;
    if (max !== undefined && parsedDraft > max) return `Valeur maximale : ${max}.`;
    return null;
  })();

  const commit = () => {
    const parsed = parseDecimalInput(draftValue);
    const validMin = min === undefined || (parsed !== null && parsed >= min);
    const validMax = max === undefined || (parsed !== null && parsed <= max);

    if (parsed !== null && validMin && validMax) {
      onChange(parsed);
      setDraftValue(String(parsed));
      return;
    }

    setDraftValue(value === null ? '' : String(value));
  };

  return (
    <label className="grid gap-1 text-xs font-bold text-slate-600">
      {label}
      <div className="flex items-center gap-2">
        <input
          type="text"
          inputMode="decimal"
          value={draftValue}
          disabled={disabled}
          onChange={(e) => {
            const next = e.target.value;
            setDraftValue(next);
            const parsed = parseDecimalInput(next);
            if (parsed !== null) onChange(parsed);
          }}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') e.currentTarget.blur();
          }}
          className={`h-10 w-full rounded-lg border px-3 text-sm font-semibold text-slate-950 outline-none focus:ring-2 disabled:bg-slate-100 disabled:text-slate-500 ${
            error
              ? 'border-red-300 focus:border-red-500 focus:ring-red-100'
              : 'border-slate-300 focus:border-slate-500 focus:ring-slate-200'
          }`}
        />
        <span className="w-14 text-xs font-bold text-slate-400">{unit}</span>
      </div>
      {error && <span className="text-xs font-semibold text-red-600">{error}</span>}
    </label>
  );
}

function draftValidationErrors(
  draft: DraftLayer,
  layers: SoilLayer[],
  slopeHeight: number,
) {
  const errors: string[] = [];
  if (!draft.name.trim()) errors.push('Le nom de la couche est obligatoire.');
  if (draft.gamma <= 0) errors.push('γ doit être supérieur à 0 kN/m³.');
  if (draft.cohesion < 0) errors.push("c' ne peut pas être négative.");
  if (!(draft.phi_deg > 0 && draft.phi_deg < 90)) errors.push("φ' doit être compris entre 0° et 90°.");

  const draftIndex = draft.mode === 'edit' ? layers.findIndex((layer) => layer.id === draft.id) : 0;
  const isLastLayer = draft.mode === 'edit' && draftIndex === layers.length - 1;
  if (!isLastLayer) {
    const otherThickness = layers.reduce((sum, layer) => (
      layer.id === draft.id ? sum : sum + (layer.thickness ?? 0)
    ), 0);
    const maxThickness = Math.max(0.1, slopeHeight - otherThickness - 0.1);
    if (draft.thickness === null || draft.thickness <= 0) {
      errors.push("L'épaisseur doit être supérieure à 0 m.");
    } else if (draft.thickness > maxThickness) {
      errors.push(`L'épaisseur dépasse la hauteur disponible (${maxThickness.toFixed(2)} m max).`);
    }
  }

  return errors;
}

export default function LayerPanel() {
  const layers = useAnalysisStore((s) => s.layers);
  const slopeHeight = useAnalysisStore((s) => s.slopeHeight);
  const setLayers = useAnalysisStore((s) => s.setLayers);
  const [draft, setDraft] = useState<DraftLayer | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const openCreate = () => {
    const fallback = emptyLayer(layers);
    setDraft({
      ...fallback,
      thickness: Math.min(2.0, Math.max(0.1, remainingThickness(layers, slopeHeight) / 2)),
      mode: 'create',
    });
  };
  const openEdit = (layer: SoilLayer) => setDraft({ ...layer, mode: 'edit' });

  const saveDraft = () => {
    if (!draft) return;
    if (draft.mode === 'create') {
      const manualThickness = Math.max(0.1, draft.thickness ?? 2.0);
      const usedBeforeNewLayer = finiteThicknessSum(layers);
      const availableThickness = Math.max(0.1, slopeHeight - usedBeforeNewLayer - 0.1);
      const cappedThickness = Math.min(manualThickness, availableThickness);
      const newTopLayer = { ...draft, thickness: cappedThickness, mode: undefined } as SoilLayer;
      const stratigraphicLayers = withBottomSubstratum([newTopLayer, ...layers]);
      setLayers(renumberAutomaticLayerNames(stratigraphicLayers));
    } else {
      const lastId = layers[layers.length - 1]?.id;
      setLayers(layers.map((l) => (
        l.id === draft.id
          ? ({ ...draft, thickness: draft.id === lastId ? null : draft.thickness, mode: undefined } as SoilLayer)
          : l
      )));
    }
    setDraft(null);
  };

  const confirmDelete = () => {
    if (deleteId === null) return;
    const filtered = layers.filter((l) => l.id !== deleteId);
    if (filtered.length > 0) {
      filtered[filtered.length - 1] = { ...filtered[filtered.length - 1], thickness: null };
    }
    setLayers(filtered);
    setDeleteId(null);
  };

  return (
    <div className="space-y-3">
      <div className="max-h-80 space-y-2 overflow-y-auto pr-1">
        {layers.map((layer, idx) => {
          const thickness = displayedThickness(layers, idx, slopeHeight);
          return (
            <div key={layer.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <strong className="rounded-full bg-white px-3 py-1 text-sm text-slate-950 shadow-sm">{layer.name}</strong>
                <div className="flex gap-1">
                  <button
                    className="rounded-full px-3 py-1 text-xs font-bold text-slate-600 hover:bg-white hover:text-slate-950"
                    onClick={() => openEdit(layer)}
                  >
                    Modifier
                  </button>
                  {layers.length > 1 && (
                    <button
                      className="rounded-full px-3 py-1 text-xs font-bold text-red-600 hover:bg-red-50 hover:text-red-700"
                      onClick={() => setDeleteId(layer.id)}
                    >
                      Supprimer
                    </button>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-4 gap-2 text-xs">
                <div className="grid gap-1 font-semibold text-slate-500">
                  <span>γ</span>
                  <span className="text-sm font-bold text-slate-950">{layer.gamma.toFixed(1)} <small className="font-medium text-slate-400">kN/m³</small></span>
                </div>
                <div className="grid gap-1 font-semibold text-slate-500">
                  <span>c'</span>
                  <span className="text-sm font-bold text-slate-950">{layer.cohesion.toFixed(0)} <small className="font-medium text-slate-400">kPa</small></span>
                </div>
                <div className="grid gap-1 font-semibold text-slate-500">
                  <span>φ'</span>
                  <span className="text-sm font-bold text-slate-950">{layer.phi_deg.toFixed(1)} <small className="font-medium text-slate-400">°</small></span>
                </div>
                <div className="grid gap-1 font-semibold text-slate-500">
                  <span>e</span>
                  <span className="text-sm font-bold text-slate-950">
                    {thickness.toFixed(2)} m
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <button
        onClick={openCreate}
        className="h-10 rounded-lg border border-slate-300 bg-white px-4 text-sm font-bold text-slate-700 transition hover:bg-slate-100"
      >
        + Ajouter une couche
      </button>

      {draft && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/55 p-6">
          <div className="w-full max-w-3xl rounded-xl bg-white shadow-2xl">
            <div className="border-b border-slate-200 p-5">
              <p className="text-xs font-black uppercase tracking-wide text-slate-500">
                {draft.mode === 'create' ? 'Nouvelle couche' : 'Modification des paramètres'}
              </p>
              <h3 className="mt-1 text-2xl font-black text-slate-950">
                {draft.mode === 'create' ? 'Ajouter une couche de sol' : `Modifier ${draft.name}`}
              </h3>
            </div>

            <div className="grid gap-4 p-5">
              {(() => {
                const validationErrors = draftValidationErrors(draft, layers, slopeHeight);
                return validationErrors.length > 0 ? (
                  <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-xs font-semibold leading-5 text-red-700">
                    {validationErrors.map((error) => (
                      <p key={error}>{error}</p>
                    ))}
                  </div>
                ) : null;
              })()}

              <label className="grid gap-1 text-xs font-bold text-slate-600">
                Nom de la couche
                <input
                  value={draft.name}
                  onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                  className="h-10 rounded-lg border border-slate-300 px-3 text-sm font-semibold text-slate-950 outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
                />
              </label>

              <div className="grid grid-cols-2 gap-4">
                {(() => {
                  const draftIndex = draft.mode === 'edit' ? layers.findIndex((layer) => layer.id === draft.id) : layers.length;
                  const isLastLayer = draft.mode === 'edit' && draftIndex === layers.length - 1;
                  const otherThickness = layers.reduce((sum, layer) => (
                    layer.id === draft.id ? sum : sum + (layer.thickness ?? 0)
                  ), 0);
                  const maxThickness = Math.max(0.1, slopeHeight - otherThickness - 0.1);
                  const thicknessValue = isLastLayer
                    ? displayedThickness(layers, draftIndex, slopeHeight)
                    : draft.thickness ?? 2.0;
                  return (
                    <>
                <NumberInput label="Poids volumique γ" unit="kN/m³" value={draft.gamma} step={0.5} min={1} onChange={(v) => setDraft({ ...draft, gamma: v })} />
                <NumberInput label="Cohésion effective c'" unit="kPa" value={draft.cohesion} step={1} min={0} onChange={(v) => setDraft({ ...draft, cohesion: v })} />
                <NumberInput label="Angle de frottement φ'" unit="°" value={draft.phi_deg} step={0.5} min={1} max={89} onChange={(v) => setDraft({ ...draft, phi_deg: v })} />
                <NumberInput
                  label={isLastLayer ? 'Épaisseur e calculée' : 'Épaisseur e'}
                  unit="m"
                  value={thicknessValue}
                  step={0.5}
                  min={0.1}
                  max={isLastLayer ? undefined : maxThickness}
                  disabled={isLastLayer}
                  onChange={(v) => setDraft({ ...draft, thickness: v })}
                />
                    </>
                  );
                })()}
              </div>

              <div className="rounded-lg bg-slate-50 p-4 text-sm font-medium leading-6 text-slate-600">
                γ est le poids volumique de la couche. c' et φ' définissent sa résistance au cisaillement
                (cohésion et angle de frottement effectifs). L'épaisseur positionne la couche dans le profil
                du talus, de haut en bas.
              </div>
            </div>

            <div className="flex justify-end gap-2 border-t border-slate-200 p-5">
              <button
                onClick={() => setDraft(null)}
                className="h-10 rounded-lg border border-slate-300 px-4 text-sm font-bold text-slate-700 hover:bg-slate-50"
              >
                Annuler
              </button>
              <button
                onClick={saveDraft}
                disabled={draftValidationErrors(draft, layers, slopeHeight).length > 0}
                className="h-10 rounded-lg bg-slate-950 px-5 text-sm font-black text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Enregistrer
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteId !== null && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/55 p-6">
          <div className="w-full max-w-md rounded-xl bg-white p-5 shadow-2xl">
            <h3 className="text-xl font-black text-slate-950">Supprimer cette couche ?</h3>
            <p className="mt-2 text-sm font-medium leading-6 text-slate-600">
              La couche inférieure sera automatiquement ajustée pour couvrir le reste du profil.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setDeleteId(null)} className="h-10 rounded-lg border border-slate-300 px-4 text-sm font-bold text-slate-700">
                Annuler
              </button>
              <button onClick={confirmDelete} className="h-10 rounded-lg bg-red-600 px-4 text-sm font-black text-white hover:bg-red-700">
                Supprimer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
