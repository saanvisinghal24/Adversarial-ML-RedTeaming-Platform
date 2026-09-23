/** App shell: a fixed left rail (wordmark + nav + account), content on an asymmetric grid. */
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../store/auth";

const NAV = [
  { to: "/models", label: "Models" },
  { to: "/scans/new", label: "New scan" },
];

export default function Layout() {
  const { email, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen lg:flex">
      <aside className="border-rule px-6 py-7 lg:relative lg:sticky lg:top-0 lg:h-screen lg:w-[260px] lg:shrink-0 lg:border-r lg:px-8 lg:py-10">
        <div className="flex items-start justify-between lg:block">
          <NavLink to="/models" className="block">
            <span className="font-display text-[19px] font-bold uppercase leading-[0.9] tracking-tightest">
              Adversarial
              <br />
              ML Red-Team
            </span>
          </NavLink>

          <nav className="flex gap-6 lg:mt-14 lg:flex-col lg:gap-3">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `text-[15px] transition-colors ${
                    isActive ? "text-ink" : "text-muted hover:text-ink"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="mt-8 hidden lg:absolute lg:bottom-10 lg:left-8 lg:right-8 lg:mt-0 lg:block">
          <p className="t-label">Signed in</p>
          <p className="mt-1 truncate text-[14px]">{email}</p>
          <button
            type="button"
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="mt-3 text-[13px] text-muted link-underline"
          >
            Sign out
          </button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 px-6 pb-24 pt-10 lg:px-14 lg:pt-16">
        <Outlet />
      </main>
    </div>
  );
}
