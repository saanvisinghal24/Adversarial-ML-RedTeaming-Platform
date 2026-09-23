import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../lib/api";
import { Notice, Reveal, Skeleton, StatusMark } from "../components/primitives";

const fmt = (iso) =>
  new Date(iso).toLocaleDateString(undefined, { day: "2-digit", month: "short" });

export default function ModelHistory() {
  const { modelId } = useParams();

  const models = useQuery({ queryKey: ["models"], queryFn: api.listModels });
  const scans = useQuery({
    queryKey: ["model-scans", modelId],
    queryFn: () => api.modelScans(modelId),
    refetchInterval: (query) =>
      query.state.data?.some((s) => s.status === "queued" || s.status === "running") ? 3000 : false,
  });

  const model = models.data?.find((m) => m.id === modelId);
  const scored = (scans.data ?? [])
    .filter((s) => s.final_score !== null && s.final_score !== undefined)
    .slice()
    .reverse()
    .map((s) => ({ date: fmt(s.created_at), score: s.final_score, grade: s.grade }));

  if (scans.isPending) return <Skeleton lines={5} />;

  if (scans.isError) {
    return (
      <Notice
        tone="error"
        title="Couldn't load this model's scans"
        action={
          <button className="btn btn-quiet" onClick={() => scans.refetch()}>
            Try again
          </button>
        }
      >
        {scans.error.message}
      </Notice>
    );
  }

  return (
    <div className="mx-auto max-w-6xl">
      <Reveal>
        <p className="t-label">Model history</p>
        <h1 className="t-display mt-3">{model?.name ?? "Model"}</h1>
        {model ? (
          <p className="mt-6 text-[15px] text-muted">
            v{model.version} · {model.model_type} · {scans.data.length} scan
            {scans.data.length === 1 ? "" : "s"}
          </p>
        ) : null}
      </Reveal>

      <section className="mt-20 rule pt-8">
        <h2 className="t-head">Score over time</h2>
        {scored.length >= 2 ? (
          <div className="mt-10 h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={scored} margin={{ top: 8, right: 12, bottom: 8, left: -18 }}>
                <CartesianGrid stroke="#DAD5CB" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "#6B655D", fontSize: 12 }}
                  tickLine={false}
                  axisLine={{ stroke: "#DAD5CB" }}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fill: "#6B655D", fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "#FAFAF8",
                    border: "1px solid #DAD5CB",
                    borderRadius: 0,
                    fontSize: 13,
                  }}
                  formatter={(value, _n, entry) => [`${value} (${entry.payload.grade})`, "score"]}
                />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#B4361E"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "#B4361E", strokeWidth: 0 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="mt-6 max-w-measure text-[15px] text-muted">
            One more finished scan and a trend line appears here. Re-scan after hardening the model
            to see whether the grade actually moved.
          </p>
        )}
      </section>

      <section className="mt-24 rule pt-8">
        <h2 className="t-head">Scans</h2>
        {scans.data.length === 0 ? (
          <Notice title="No scans yet">
            <Link to={`/scans/new?model=${modelId}`} className="link-underline">
              Configure the first one
            </Link>
            .
          </Notice>
        ) : (
          <ul className="mt-6">
            {scans.data.map((scan, i) => (
              <li key={scan.id} className="rule">
                <Link
                  to={`/scans/${scan.id}`}
                  className="grid grid-cols-2 items-baseline gap-4 py-6 lg:grid-cols-12"
                >
                  <span className="t-label t-data lg:col-span-1">
                    {String(scans.data.length - i).padStart(2, "0")}
                  </span>
                  <span className="text-[15px] lg:col-span-4">
                    {new Date(scan.created_at).toLocaleString()}
                  </span>
                  <span className="lg:col-span-3">
                    <StatusMark status={scan.status} />
                  </span>
                  <span className="t-data text-[15px] lg:col-span-4 lg:text-right">
                    {scan.final_score !== null && scan.final_score !== undefined
                      ? `${scan.final_score.toFixed(1)} · ${scan.grade}`
                      : "—"}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
