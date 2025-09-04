"use client";
import { useMemo, useRef, useState } from "react";
import STLViewer from "../components/STLViewer";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

type Dimensions = { L: number; W: number; H: number };

type Proposal = {
  type: "snug" | "easy" | "multi";
  x_slots: number;
  y_slots: number;
  z_units: number;
  clearance: number;
  compartments?: number | null;
};

export default function Page() {
  const [itemName, setItemName] = useState("");
  const [itemId, setItemId] = useState("");
  const [dims, setDims] = useState<Dimensions>({ L: 152, W: 106, H: 60 });
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [selected, setSelected] = useState<Proposal | null>(null);
  const [stlUrl, setStlUrl] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");

  const validDims = useMemo(() => dims.L > 0 && dims.W > 0 && dims.H > 0, [dims]);

  async function handleIdentify() {
    setError("");
    setProposals([]);
    setSelected(null);
    setStlUrl("");
    try {
      const res = await fetch(`${API_BASE}/identify`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ input: itemName })
      });
      const data = await res.json();
      const first = data?.candidates?.[0];
      if (!first) throw new Error("No candidates returned");
      setItemId(first.id);
      // Try to prefill dimensions
      const dres = await fetch(`${API_BASE}/dimensions?id=${encodeURIComponent(first.id)}`);
      if (dres.ok) {
        const dd = await dres.json();
        if (dd?.dims_mm) setDims(dd.dims_mm);
      }
    } catch (e:any) {
      setError(e.message || "Identify failed");
    }
  }

  async function handleProposals() {
    setError("");
    setProposals([]);
    setSelected(null);
    setStlUrl("");
    try {
      const res = await fetch(`${API_BASE}/proposals`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ item_id: itemId || "manual", dims_mm: dims, options: {} })
      });
      if (!res.ok) throw new Error(`Proposals failed (${res.status})`);
      const data = await res.json();
      setProposals(data?.proposals || []);
    } catch (e:any) {
      setError(e.message || "Proposals failed");
    }
  }

  async function handleSTL(p: Proposal) {
    setError("");
    setSelected(p);
    setStlUrl("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/stl`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ item_id: itemId || "manual", dims_mm: dims, proposal: p, options: { lip: true }, label: itemName || undefined })
      });
      if (!res.ok) throw new Error(`STL failed (${res.status})`);
      const data = await res.json();
      const file = data?.files?.[0]?.url;
      if (!file) throw new Error("No STL URL");
      setStlUrl(`${API_BASE}${file}`);
    } catch (e:any) {
      setError(e.message || "STL generation failed");
    } finally {
      setLoading(false);
    }
  }

  function useDemo() {
    setItemName("Nintendo Switch Pro Controller");
    setItemId("Qnintendo_switch_pro");
    setDims({ L: 152, W: 106, H: 60 });
  }

  return (
    <main className="space-y-6">
      <section className="grid md:grid-cols-2 gap-4">
        <div className="space-y-3 p-4 rounded-2xl bg-white/5">
          <h2 className="text-lg font-semibold">1) Item</h2>
          <div className="flex gap-2">
            <input
              value={itemName}
              onChange={(e) => setItemName(e.target.value)}
              placeholder="Describe your item (e.g., Nintendo Switch Pro Controller)"
              className="w-full px-3 py-2 rounded-xl bg-white/10 focus:outline-none"
            />
            <button onClick={handleIdentify} className="px-3 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50" disabled={!itemName}>Identify</button>
            <button onClick={useDemo} className="px-3 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500">Demo</button>
          </div>
          <p className="text-xs opacity-70">ID: {itemId || "(none)"}</p>
        </div>
        <div className="space-y-3 p-4 rounded-2xl bg-white/5">
          <h2 className="text-lg font-semibold">2) Dimensions (mm)</h2>
          <div className="grid grid-cols-3 gap-3">
            {(["L","W","H"] as const).map((k) => (
              <div key={k} className="space-y-1">
                <label className="block text-sm opacity-80">{k}</label>
                <input type="number" inputMode="decimal" value={dims[k]} onChange={(e) => setDims({ ...dims, [k]: Number(e.target.value) })} className="w-full px-3 py-2 rounded-xl bg-white/10 focus:outline-none"/>
              </div>
            ))}
          </div>
          <button onClick={handleProposals} className="px-3 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50" disabled={!validDims}>Generate proposals</button>
        </div>
      </section>

      {error && (
        <div className="p-3 rounded-xl bg-red-600/30 border border-red-500/50">{error}</div>
      )}

      {proposals.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">3) Pick a proposal</h2>
          <div className="grid md:grid-cols-3 gap-4">
            {proposals.map((p) => (
              <div key={p.type} className={`p-4 rounded-2xl bg-white/5 border ${selected?.type === p.type ? "border-emerald-500" : "border-white/10"}`}>
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold capitalize">{p.type}</h3>
                  <span className="text-xs opacity-70">{p.clearance} mm clr</span>
                </div>
                <p className="text-sm opacity-80 mt-1">{p.x_slots} × {p.y_slots} slots · {p.z_units} Z-units</p>
                {typeof p.compartments === "number" && (
                  <p className="text-xs opacity-70">{p.compartments} compartments</p>
                )}
                <button disabled={loading} onClick={() => handleSTL(p)} className="mt-3 w-full px-3 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50">Generate STL</button>
              </div>
            ))}
          </div>
        </section>
      )}

      {stlUrl && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">4) Preview STL</h2>
          <p className="text-sm opacity-80">Download: <a className="underline" href={stlUrl} target="_blank" rel="noreferrer">{stlUrl}</a></p>
          <div className="h-[480px] rounded-2xl overflow-hidden border border-white/10">
            <STLViewer url={stlUrl} />
          </div>
        </section>
      )}
    </main>
  );
}
