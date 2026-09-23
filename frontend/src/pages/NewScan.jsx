import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Notice, Reveal, Skeleton } from "../components/primitives";

/** Defaults mirror ARCHITECTURE.md contract #3 — change them there first, then here. */
const ATTACKS = [
  {
    id: "fgsm",
    title: "FGSM",
    blurb: "One-step gradient evasion. Fast, and the baseline every robustness claim is measured against.",
    threat: "white_box",
    params: [{ key: "epsilon", label: "Epsilon", value: 0.05, step: 0.01 }],
  },
  {
    id: "pgd",
    title: "PGD",
    blurb: "Iterative projected descent. Slower, and usually the attack that actually breaks the model.",
    threat: "white_box",
    params: [
      { key: "epsilon", label: "Epsilon", value: 0.05, step: 0.01 },
      { key: "step_size", label: "Step size", value: 0.01, step: 0.005 },
      { key: "iterations", label: "Iterations", value: 40, step: 5 },
    ],
  },
  {
    id: "hopskipjump",
    title: "HopSkipJump",
    blurb: "Decision-based, no gradients. Models the attacker who only has your prediction endpoint.",
    threat: "black_box",
    params: [{ key: "query_budget", label: "Query budget", value: 2000, step: 100 }],
  },
  {
    id: "poisoning",
    title: "Label flipping",
    blurb: "Contaminates the training set at 1 / 5 / 10 percent and retrains, measuring what accuracy costs.",
    threat: "white_box",
    params: [],
  },
];

export default function NewScan() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const models = useQuery({ queryKey: ["models"], queryFn: api.listModels });
  const [modelId, setModelId] = useState(searchParams.get("model") ?? "");
  const [selected, setSelected] = useState(["fgsm", "pgd"]);
  const [params, setParams] = useState(() =>
    Object.fromEntries(
      ATTACKS.map((a) => [a.id, Object.fromEntries(a.params.map((p) => [p.key, p.value]))]),
    ),
  );

  const threatModel = useMemo(
    () => (selected.includes("hopskipjump") && selected.length === 1 ? "black_box" : "white_box"),
    [selected],
  );

  const effectiveModelId = modelId || models.data?.[0]?.id || "";

  const create = useMutation({
    mutationFn: () =>
      api.createScan({
        model_id: effectiveModelId,
        threat_model: threatModel,
        attacks: selected,
        params: Object.fromEntries(selected.map((id) => [id, params[id]])),
      }),
    onSuccess: (scan) => navigate(`/scans/${scan.id}`),
  });

  function toggle(id) {
    setSelected((current) =>
      current.includes(id) ? current.filter((x) => x !== id) : [...current, id],
    );
  }

  if (models.isPending) return <Skeleton lines={5} />;

  if (models.data?.length === 0) {
    return (
      <Notice title="Upload a model first">
        A scan needs an artefact to attack. Head to Models and upload a .pkl, .onnx or .pt file.
      </Notice>
    );
  }

  return (
    <div className="mx-auto max-w-6xl">
      <Reveal>
        <h1 className="t-display">
          Configure
          <br />
          the scan
        </h1>
      </Reveal>

      <form
        className="mt-20"
        onSubmit={(e) => {
          e.preventDefault();
          if (selected.length) create.mutate();
        }}
      >
        <section className="rule pt-8 lg:grid lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:gap-16">
          <h2 className="t-head">Target</h2>
          <div className="mt-6 lg:mt-1">
            <label htmlFor="model" className="t-label">
              Model
            </label>
            <select
              id="model"
              className="field mt-2"
              value={effectiveModelId}
              onChange={(e) => setModelId(e.target.value)}
            >
              {models.data.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} — v{m.version} ({m.model_type})
                </option>
              ))}
            </select>
            <p className="mt-3 text-[13px] text-muted">
              Threat model resolves to <span className="text-ink">{threatModel.replace("_", "-")}</span>{" "}
              from the attacks you pick.
            </p>
          </div>
        </section>

        <section className="mt-20 rule pt-8 lg:grid lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:gap-16">
          <div>
            <h2 className="t-head">Attacks</h2>
            <p className="mt-4 max-w-measure text-[15px] text-muted">
              Each one runs in the same sandboxed job and contributes to a weighted component of the
              final grade.
            </p>
          </div>

          <ul className="mt-8 lg:mt-1">
            {ATTACKS.map((attack) => {
              const on = selected.includes(attack.id);
              return (
                <li key={attack.id} className="rule">
                  <div className="py-7">
                    <label className="flex cursor-pointer items-start gap-5">
                      <input
                        type="checkbox"
                        checked={on}
                        onChange={() => toggle(attack.id)}
                        className="mt-1.5 h-4 w-4 shrink-0 accent-[#B4361E]"
                      />
                      <span>
                        <span className="t-sub">{attack.title}</span>
                        <span className="ml-3 text-[12px] uppercase tracking-[0.14em] text-muted">
                          {attack.threat.replace("_", "-")}
                        </span>
                        <span className="mt-1.5 block max-w-measure text-[14px] text-muted">
                          {attack.blurb}
                        </span>
                      </span>
                    </label>

                    {on && attack.params.length > 0 ? (
                      <div className="ml-9 mt-5 flex flex-wrap gap-8">
                        {attack.params.map((p) => (
                          <div key={p.key} className="w-32">
                            <label htmlFor={`${attack.id}-${p.key}`} className="t-label">
                              {p.label}
                            </label>
                            <input
                              id={`${attack.id}-${p.key}`}
                              type="number"
                              step={p.step}
                              min={0}
                              className="field t-data mt-1 py-1.5"
                              value={params[attack.id][p.key]}
                              onChange={(e) =>
                                setParams((prev) => ({
                                  ...prev,
                                  [attack.id]: {
                                    ...prev[attack.id],
                                    [p.key]: Number(e.target.value),
                                  },
                                }))
                              }
                            />
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>

        <div className="mt-14 flex flex-wrap items-center gap-6">
          <button type="submit" className="btn btn-solid" disabled={!selected.length || create.isPending}>
            {create.isPending ? "Queueing" : "Start scan"}
          </button>
          <p className="text-[14px] text-muted">
            {selected.length
              ? `${selected.length} attack${selected.length > 1 ? "s" : ""} selected`
              : "Pick at least one attack"}
          </p>
        </div>

        {create.isError ? (
          <p role="alert" className="mt-6 border-l-2 border-signal pl-4 text-[14px] text-signal">
            {create.error.message}
          </p>
        ) : null}
      </form>
    </div>
  );
}
