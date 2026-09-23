import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Notice, Reveal, Skeleton } from "../components/primitives";

const MODEL_TYPES = [
  ["sklearn", ".pkl"],
  ["xgboost", ".pkl"],
  ["pytorch", ".pt"],
  ["onnx", ".onnx"],
];

function bytes(n) {
  if (!n) return "—";
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export default function Models() {
  const queryClient = useQueryClient();
  const fileInput = useRef(null);
  const [file, setFile] = useState(null);
  const [name, setName] = useState("");
  const [modelType, setModelType] = useState("sklearn");
  const [version, setVersion] = useState("1");

  const models = useQuery({ queryKey: ["models"], queryFn: api.listModels });

  const upload = useMutation({
    mutationFn: () => {
      const form = new FormData();
      form.append("name", name || file.name.replace(/\.[^.]+$/, ""));
      form.append("model_type", modelType);
      form.append("version", version);
      form.append("file", file);
      return api.uploadModel(form);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      setFile(null);
      setName("");
      if (fileInput.current) fileInput.current.value = "";
    },
  });

  return (
    <div className="mx-auto max-w-6xl">
      <Reveal>
        <h1 className="t-display">Models</h1>
        <p className="mt-6 max-w-measure text-[16px] text-muted">
          Everything you&apos;ve uploaded, and every scan run against it. Artefacts are hashed on
          upload so a re-scan is always traceable to the exact file that was tested.
        </p>
      </Reveal>

      {/* 01 — upload. Asymmetric: form on the left third, guidance on the right. */}
      <section className="mt-20 rule pt-8 lg:grid lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-16">
        <div>
          <h2 className="t-head">Upload a model</h2>

          <form
            className="mt-9 space-y-7"
            onSubmit={(e) => {
              e.preventDefault();
              if (file) upload.mutate();
            }}
          >
            <div>
              <label htmlFor="file" className="t-label">
                Artefact
              </label>
              <input
                id="file"
                ref={fileInput}
                type="file"
                accept=".pkl,.onnx,.pt"
                required
                className="field mt-2 file:mr-4 file:border file:border-ink file:bg-transparent file:px-3 file:py-1.5 file:text-[12px] file:uppercase file:tracking-[0.1em]"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <p className="mt-2 text-[13px] text-muted">
                {file ? `${file.name} · ${bytes(file.size)}` : "Accepts .pkl, .onnx or .pt, up to 200 MB."}
              </p>
            </div>

            <div className="grid gap-7 sm:grid-cols-3">
              <div className="sm:col-span-2">
                <label htmlFor="name" className="t-label">
                  Name
                </label>
                <input
                  id="name"
                  className="field mt-2"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="phishing-url-rf"
                />
              </div>
              <div>
                <label htmlFor="version" className="t-label">
                  Version
                </label>
                <input
                  id="version"
                  className="field mt-2"
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                />
              </div>
            </div>

            <fieldset>
              <legend className="t-label">Framework</legend>
              <div className="mt-3 flex flex-wrap gap-2">
                {MODEL_TYPES.map(([value, ext]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setModelType(value)}
                    className={`border px-4 py-2 text-[13px] transition-colors ${
                      modelType === value
                        ? "border-ink bg-ink text-paper"
                        : "border-rule text-muted hover:border-ink hover:text-ink"
                    }`}
                  >
                    {value} <span className="opacity-60">{ext}</span>
                  </button>
                ))}
              </div>
            </fieldset>

            {upload.isError ? (
              <p role="alert" className="border-l-2 border-signal pl-4 text-[14px] text-signal">
                {upload.error.message}
              </p>
            ) : null}

            <button type="submit" className="btn btn-solid" disabled={!file || upload.isPending}>
              {upload.isPending ? "Uploading" : "Upload model"}
            </button>
          </form>
        </div>

        <aside className="mt-14 border-t border-rule pt-8 lg:mt-2 lg:border-l lg:border-t-0 lg:pl-12 lg:pt-0">
          <p className="max-w-measure text-[15px] leading-relaxed text-muted">
            The file is never executed by the API. It&apos;s stored, hashed, and mounted read-only
            into the attack sandbox when a scan runs, so a malicious artefact can&apos;t reach the
            backend process.
          </p>
          <p className="mt-5 max-w-measure text-[15px] leading-relaxed text-muted">
            Upload the same model again with a new version number to track whether hardening
            actually moved the grade.
          </p>
        </aside>
      </section>

      {/* 02 — the list */}
      <section className="mt-24 rule pt-8">
        <h2 className="t-head">Uploaded</h2>

        <div className="mt-8">
          {models.isPending ? <Skeleton lines={4} /> : null}

          {models.isError ? (
            <Notice
              tone="error"
              title="Couldn't load your models"
              action={
                <button className="btn btn-quiet" onClick={() => models.refetch()}>
                  Try again
                </button>
              }
            >
              {models.error.message}
            </Notice>
          ) : null}

          {models.data?.length === 0 ? (
            <Notice title="Nothing uploaded yet">
              Upload a .pkl, .onnx or .pt classifier above to run your first scan.
            </Notice>
          ) : null}

          <ul>
            {models.data?.map((model, i) => (
              <li key={model.id} className="rule">
                <div className="grid grid-cols-2 items-baseline gap-4 py-6 lg:grid-cols-12">
                  <span className="t-label t-data lg:col-span-1">{String(i + 1).padStart(2, "0")}</span>
                  <div className="lg:col-span-4">
                    <p className="t-sub">{model.name}</p>
                    <p className="mt-1 text-[13px] text-muted">
                      v{model.version} · {model.model_type} · {bytes(model.size_bytes)}
                    </p>
                  </div>
                  <p className="col-span-2 break-all font-mono text-[11px] text-muted lg:col-span-4">
                    {model.checksum_sha256?.slice(0, 32)}…
                  </p>
                  <div className="col-span-2 flex gap-5 lg:col-span-3 lg:justify-end">
                    <Link to={`/models/${model.id}`} className="text-[14px] link-underline">
                      History
                    </Link>
                    <Link
                      to={`/scans/new?model=${model.id}`}
                      className="text-[14px] text-signal link-underline"
                    >
                      Run a scan
                    </Link>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
