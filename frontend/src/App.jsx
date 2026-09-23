import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import ModelHistory from "./pages/ModelHistory";
import Models from "./pages/Models";
import NewScan from "./pages/NewScan";
import ScanDetail from "./pages/ScanDetail";
import { useIsAuthed } from "./store/auth";

function RequireAuth({ children }) {
  return useIsAuthed() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const authed = useIsAuthed();

  return (
    <Routes>
      <Route path="/login" element={authed ? <Navigate to="/models" replace /> : <Login />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/models" element={<Models />} />
        <Route path="/models/:modelId" element={<ModelHistory />} />
        <Route path="/scans/new" element={<NewScan />} />
        <Route path="/scans/:scanId" element={<ScanDetail />} />
      </Route>
      <Route path="*" element={<Navigate to={authed ? "/models" : "/login"} replace />} />
    </Routes>
  );
}
