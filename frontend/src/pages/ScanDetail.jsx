import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../lib/api";
import {
  GradeMark,
  Notice,
  Reveal,
  SeverityTag,
  Skeleton,
  StatusMark,
} from "../components/primitives";

const POLL_MS = 2000;

/** Flattens contract #4 into the per-attack bars the chart needs. */
function asrSeries(raw) {
  if (!raw) return [];
  const rows = [];
  for (const [attack, block] of Object.entries(raw.evasion ?? {})) {
    rows.push({ name: attack.toUpperCase(), value: block.asr ?? 0, kind: "evasion" });
  }
  for (const [attack, block] of Object.entries(raw.black_box ?? {})) {
    rows.push({ name: attack.toUpperCase(), value: block.asr ?? 0, kind: "black-box" });
  }
  for (const [level, block] of Object.entries(raw.poisoning ?? {})) {
    rows.push({ name: `POISON ${level}`, value: block.accuracy_drop ?? 0, kind: "poisoning" });
  }
  return rows;
}

function barColour(value) {
  if (value >= 0.6) return "#B4361E";
  if (value >= 0.3) return "#8A6A1F";
  return "#3F5B43";
}

/** Checklist ticks are the user's own working state — kept in the browser, not the API. */
function useChecklist(scanId) {
  const key = `redteam-mitigations-${scanId}`;
  const [done, setDone] = useState(() => {
    try {
      return new Set(JSON.parse(localStorage.getItem(key) ?? "[]"));
    } catch {
      return new Set();
    }
  });

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify([...done]));
  }, [key, done]);

  return [
    done,
    (id) =>
      setDone((prev) => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return next;
      }),
  ];
}

export default function ScanDetail() {
  const { scanId } = useParams();
  const [checked, toggleChecked] = useChecklist(scanId);

  const scan = useQuery({
    queryKey: ["scan", scanId],
    queryFn: () => api.getScan(scanId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "queued" || status === "running" ? POLL_MS : false;
    },
    retry: 1,
  });

  const series = useMemo(() => asrSeries(scan.data?.raw_results), [scan.data]);

  if (scan.isPending) return <Skeleton lines={6} />;

  if (scan.isError) {
    return (
      <Notice
        tone="error"
        title="Couldn't load this scan"
        action={
          <button className="btn btn-quiet" onClick={() => scan.refetch()}>
            Try again
          </button>
        }
      >
        {scan.error.message}
      </Notice>
    );
  }

  const data = scan.data;
  const running = data.status === "queued" || data.status === "running";
  const attacks = data.attack_config?.attacks ?? [];

  return (
    <div className="mx-auto max-w-6xl">
      <Reveal>
        <p className="t-label">Scan {scanId.slice(0, 8)}</p>
        <h1 className="t-display mt-3">
          {data.status === "failed" ? "Scan failed" : running ? "Running" : "Scan results"}
        </h1>
        <div className="mt-6 flex flex-wrap items-center gap-x-8 gap-y-3 text-[14px] text-muted">
          <StatusMark status={data.status} />
          <span>{data.threat_model.replace("_", "-")}</span>
          <span>{attacks.join(" · ")}</span>
          <Link to={`/models/${data.model_id}`} className="link-underline">
            Model history
          </Link>
        </div>
      </Reveal>

      {running ? (
        <section className="mt-20 rule pt-8">
          <h2 className="t-head">Working</h2>
          <p className="mt-5 max-w-measure text-[15px] text-muted">
            The sandbox is loading the artefact and running {attacks.length} attack
            {attacks.length > 1 ? "s" : ""}. This page updates itself every couple of seconds —
            nothing to click. Poisoning runs retrain the model, so they take the longest.
          </p>
          <div className="mt-8 h-px w-full overflow-hidden bg-rule">
            <div className="h-px w-1/3 animate-pulse bg-signal" />
          </div>
        </section>
      ) : null}

      {data.status === "failed" ? (
        <section className="mt-20 rule pt-8">
          <Notice
            tone="error"
            title="The sandbox didn't finish"
            action={
              <Link to={`/scans/new?model=${data.model_id}`} className="btn btn-quiet">
                Configure a new scan
              </Link>
            }
          >
            {data.error ?? "No error detail was recorded."}
          </Notice>
        </section>
      ) : null}

      {data.status === "done" && data.score ? (
        <>
          {/* 01 — the grade. This is the one loud element on the page. */}
          <section className="mt-20 rule pt-8 lg:grid lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
            <div>
              <h2 className="t-head">Robustness</h2>
              <div className="mt-8">
                <GradeMark grade={data.score.grade} score={data.score.final_score_0_100} />
              </div>
            </div>

            <dl className="mt-12 lg:mt-3">
              {Object.entries(data.score.component_scores).map(([component, value]) => (
                <div key={component} className="rule py-4">
                  <div className="flex items-baseline justify-between">
                    <dt className="text-[15px] capitalize">{component.replace("_", "-")}</dt>
                    <dd className="t-data text-[15px]">
                      {value.toFixed(3)}
                      <span className="ml-3 text-[12px] text-muted">
                        weight {data.score.weights[component]?.toFixed(2)}
                      </span>
                    </dd>
                  </div>
                  <div className="mt-3 h-1 w-full bg-panel">
                    <div
                      className="h-1"
                      style={{
                        width: `${Math.min(value * 100, 100)}%`,
                        background: barColour(value),
                      }}
                    />
                  </div>
                </div>
              ))}
              <p className="mt-5 text-[13px] text-muted">
                Components are badness scores from 0 to 1; the grade is 100 minus their weighted sum.
                Clean accuracy before any attack was {data.raw_results?.clean_accuracy ?? "—"}.
              </p>
            </dl>
          </section>

          {/* 02 — attack success rates */}
          <section className="mt-24 rule pt-8">
            <h2 className="t-head">Attack success</h2>
            <p className="mt-4 max-w-measure text-[15px] text-muted">
              Share of attempted samples that flipped the prediction. Poisoning bars show accuracy
              lost at each contamination level instead.
            </p>
            <div className="mt-10 h-[320px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={series} margin={{ top: 8, right: 8, bottom: 8, left: -18 }}>
                  <CartesianGrid stroke="#DAD5CB" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: "#6B655D", fontSize: 12 }}
                    tickLine={false}
                    axisLine={{ stroke: "#DAD5CB" }}
                  />
                  <YAxis
                    domain={[0, 1]}
                    tick={{ fill: "#6B655D", fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    cursor={{ fill: "rgba(20,18,16,0.04)" }}
                    contentStyle={{
                      background: "#FAFAF8",
                      border: "1px solid #DAD5CB",
                      borderRadius: 0,
                      fontSize: 13,
                    }}
                    formatter={(value, _n, entry) => [value.toFixed(2), entry.payload.kind]}
                  />
                  <Bar dataKey="value" maxBarSize={64}>
                    {series.map((row) => (
                      <Cell key={row.name} fill={barColour(row.value)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* 03 — ATLAS mapping */}
          <section className="mt-24 rule pt-8">
            <h2 className="t-head">ATLAS mapping</h2>
            <div className="mt-8 overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-[14px]">
                <thead>
                  <tr className="border-b border-rule">
                    {["Attack", "Tactic", "Technique", "Severity", "OWASP ML", "NIST AI RMF"].map(
                      (head) => (
                        <th key={head} className="t-label py-3 pr-6 font-normal">
                          {head}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {data.findings.map((f) => (
                    <tr key={`${f.attack}-${f.atlas_technique}`} className="border-b border-rule">
                      <td className="py-4 pr-6 font-medium uppercase">{f.attack}</td>
                      <td className="t-data py-4 pr-6">{f.atlas_tactic}</td>
                      <td className="t-data py-4 pr-6">{f.atlas_technique}</td>
                      <td className="py-4 pr-6">
                        <SeverityTag severity={f.severity} />
                      </td>
                      <td className="py-4 pr-6 text-muted">{f.owasp_ml_top10 ?? "—"}</td>
                      <td className="py-4 pr-6 text-muted">{f.nist_ai_rmf ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* 04 — remediation, in the order it should be worked through */}
          <section className="mt-24 rule pt-8">
            <div className="flex flex-wrap items-baseline justify-between gap-4">
              <h2 className="t-head">What to fix</h2>
              <p className="text-[14px] text-muted">
                {checked.size} of {data.findings.length} done
              </p>
            </div>

            <ol className="mt-8">
              {data.findings.map((f, i) => {
                const id = `${f.attack}-${f.atlas_technique}`;
                const isDone = checked.has(id);
                return (
                  <li key={id} className="rule">
                    <label className="flex cursor-pointer items-start gap-5 py-7">
                      <input
                        type="checkbox"
                        checked={isDone}
                        onChange={() => toggleChecked(id)}
                        className="mt-1.5 h-4 w-4 shrink-0 accent-[#B4361E]"
                      />
                      <span className="t-label t-data mt-1 w-8 shrink-0">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span className={isDone ? "opacity-45" : undefined}>
                        <span className="flex flex-wrap items-center gap-3">
                          <span className="t-sub">{f.attack}</span>
                          <SeverityTag severity={f.severity} />
                          <span className="t-data text-[13px] text-muted">
                            {Object.entries(f.evidence ?? {})
                              .map(([k, v]) => `${k} ${v}`)
                              .join(" · ")}
                          </span>
                        </span>
                        <span className="mt-2 block max-w-measure text-[15px] leading-relaxed">
                          {f.mitigation}
                        </span>
                      </span>
                    </label>
                  </li>
                );
              })}
            </ol>
          </section>

          {/* 05 — export */}
          <section className="mt-24 rule pt-8 lg:grid lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
            <div>
              <h2 className="t-head">Report</h2>
              <p className="mt-5 max-w-measure text-[15px] text-muted">
                A single document with the grade, every attack outcome, and the ATLAS and compliance
                references for each finding — the thing you hand to a reviewer.
              </p>
            </div>
            <div className="mt-8 flex flex-wrap gap-4 lg:mt-2">
              <a className="btn btn-solid" href={api.reportUrl(scanId, "pdf")}>
                Download PDF
              </a>
              <a
                className="btn btn-ghost"
                href={api.reportUrl(scanId, "html")}
                target="_blank"
                rel="noreferrer"
              >
                View as page
              </a>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
