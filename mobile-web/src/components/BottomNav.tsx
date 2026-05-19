import { NavLink } from "react-router-dom";

const links = [
  { to: "/home", label: "首页" },
  { to: "/weight", label: "晨重" },
  { to: "/meals", label: "餐食" },
  { to: "/reports", label: "报表" },
  { to: "/settings", label: "设置" }
];

export function BottomNav() {
  return (
    <nav className="bottom-nav" aria-label="主导航">
      {links.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          className={({ isActive }) => (isActive ? "bottom-nav-link bottom-nav-link-active" : "bottom-nav-link")}
        >
          <span>{link.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
