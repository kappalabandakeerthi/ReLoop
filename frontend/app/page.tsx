"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import Image from "next/image";
import {
  Activity,
  ArrowRight,
  BadgeCheck,
  CheckCircle2,
  CircleAlert,
  ClipboardCheck,
  Clock3,
  Cpu,
  LayoutDashboard,
  LogOut,
  MapPin,
  Monitor,
  Package,
  Plus,
  RefreshCw,
  Recycle,
  Search,
  ShieldCheck,
  Smartphone,
  Tablet,
  UserRound,
  Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { apiRequest } from "@/lib/api";

type View = "overview" | "devices" | "assessment" | "providers" | "recovery" | "admin";
type Notice = { tone: "success" | "error"; text: string };
type UserProfile = { id: string; email: string; full_name: string; role: string; city?: string | null };
type TokenResponse = { access_token: string; user_id: string; email: string; full_name: string; role: string };
type Category = { id: number; name: string; description?: string | null; icon?: string | null };
type ClassificationResult = {
  success: boolean;
  filename: string;
  predicted_category: string;
  confidence: number;
  suggested_app_category: string;
  top_predictions: {
    category: string;
    confidence: number;
  }[];
};
type Device = {
  id: string; category_id: number; category_name?: string | null; name: string; brand: string;
  model: string; purchase_year?: number | null; approximate_age_years?: number | null;
  working_condition: string; powers_on?: boolean | null; physically_damaged?: boolean | null;
  contains_personal_data: boolean;
};
type Assessment = {
  id: string; device_id: string; overall_condition: string; functional_status: string; created_at: string;
};
type Score = {
  route: string; is_eligible: boolean; final_score: number; financial_score: number;
  useful_life_score: number; convenience_score: number; reuse_score: number;
  ineligible_reason?: string | null; score_breakdown: { evaluation_notes?: string[] };
};
type Recommendation = {
  id: string; assessment_id: string; device_id: string; recommended_route: string;
  overall_score: number; summary: string; explanation: string; weights_used: Record<string, number>;
  scores: Score[]; eligible_routes_ranked: string[]; ineligible_routes: string[];
  device_info?: { name?: string; category?: string; brand?: string; model?: string };
  financial_summary?: {
    estimated_repair_cost?: number | null;
    estimated_resale_value?: number | null;
    estimated_replacement_cost?: number | null;
    expected_remaining_life_years?: number | null;
    estimate_method?: string;
    estimate_confidence?: string;
    estimate_sources?: Record<string, string>;
    estimate_notes?: string[];
    estimate_ranges?: Record<string, { low: number; high: number }>;
    matched_faults?: string[];
    is_market_quote?: boolean;
  };
};
type Provider = {
  id: string; name: string; category: string; address: string; city: string;
  contact_email?: string | null; contact_phone?: string | null; website?: string | null;
  services_offered: string[]; operating_hours?: string | null; is_verified: boolean;
  is_sample: boolean; rating?: number | null;
};
type Recovery = {
  id: string; device_id: string; device_name?: string | null; device_category?: string | null;
  selected_route: string; provider_name?: string | null; current_status: string; tracking_code: string;
  status_history: { id: string; status: string; notes?: string | null; created_at: string }[];
  created_at: string;
};
type AdminStats = {
  kpis: Record<string, number>;
  recovery_by_status: { status: string; count: number }[];
  recommendations_by_route: { route: string; count: number }[];
  recent_requests: { id: string; tracking_code: string; device_name: string; selected_route: string; current_status: string }[];
};
type AdminRequest = {
  id: string; tracking_code: string; user_email: string; user_name: string; device_name: string;
  selected_route: string; provider_name: string; current_status: string;
};
type AdminUser = { id: string; full_name: string; email: string; role: string; city?: string | null; device_count: number; assessment_count: number };
type AdminAssessment = { id: string; user_email: string; device_name: string; category: string; overall_condition: string; recommended_route: string; overall_score?: number | null };

const navItems: { id: View; label: string; icon: LucideIcon }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "devices", label: "My devices", icon: Package },
  { id: "assessment", label: "Assess device", icon: ClipboardCheck },
  { id: "providers", label: "Providers", icon: MapPin },
  { id: "recovery", label: "Recovery tracking", icon: RefreshCw },
];
const viewPaths: Record<View, string> = {
  overview: "/dashboard",
  devices: "/devices",
  assessment: "/assessment",
  providers: "/providers",
  recovery: "/recovery",
  admin: "/admin",
};
const pathViews: Record<string, View> = {
  "/dashboard": "overview",
  "/devices": "devices",
  "/assessment": "assessment",
  "/recommendations": "assessment",
  "/providers": "providers",
  "/recovery": "recovery",
  "/admin": "admin",
};
const recoveryStatuses = [
  "Request Created", "Provider Selected", "Device Submitted / Collected",
  "Device Under Assessment", "Recovery in Progress", "Completed",
];
function errorText(error: unknown) {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

function optionalNumber(value: FormDataEntryValue | null) {
  if (value === null || String(value).trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function conditionLabel(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function estimateMoney(value?: number | null) {
  return value == null ? "Unavailable" : new Intl.NumberFormat("en-US", {
    style: "currency", currency: "USD", maximumFractionDigits: 0,
  }).format(value);
}

function estimateMoneyRange(value?: number | null, range?: { low: number; high: number }) {
  if (!range) return estimateMoney(value);
  return `${estimateMoney(range.low)}–${estimateMoney(range.high)}`;
}

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [view, updateView] = useState<View>("overview");
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authScreen, setAuthScreen] = useState<"landing" | "auth">("landing");
  const [categories, setCategories] = useState<Category[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [recoveries, setRecoveries] = useState<Recovery[]>([]);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [selectedRoute, setSelectedRoute] = useState("");
  const [selectedProviderId, setSelectedProviderId] = useState("");
  const [providerCategory, setProviderCategory] = useState("");
  const [cityFilter, setCityFilter] = useState("");
  const [providerSearch, setProviderSearch] = useState("");
  const [adminStats, setAdminStats] = useState<AdminStats | null>(null);
  const [adminRequests, setAdminRequests] = useState<AdminRequest[]>([]);
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([]);
  const [adminAssessments, setAdminAssessments] = useState<AdminAssessment[]>([]);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [classifying, setClassifying] = useState(false);
const [classification, setClassification] = useState<ClassificationResult | null>(null);
const [classificationError, setClassificationError] = useState("");

  function setView(nextView: View) {
    updateView(nextView);
    const path = viewPaths[nextView];
    if (window.location.pathname !== path) window.history.pushState({}, "", path);
  }

  function openAuth(mode: "login" | "register") {
    setAuthMode(mode);
    setAuthScreen("auth");
    const path = mode === "login" ? "/login" : "/register";
    if (window.location.pathname !== path) window.history.pushState({}, "", path);
  }

  useEffect(() => {
    const restoreRoute = () => {
      const path = window.location.pathname;
      if (path === "/login" || path === "/register") {
        setAuthMode(path === "/login" ? "login" : "register");
        setAuthScreen("auth");
        return;
      }
      const nextView = pathViews[path];
      if (nextView) {
        updateView(nextView);
        setAuthMode("login");
        setAuthScreen("auth");
      } else {
        updateView("overview");
        setAuthScreen("landing");
      }
    };
    restoreRoute();
    window.addEventListener("popstate", restoreRoute);
    setToken(window.sessionStorage.getItem("reloop_access_token"));
    apiRequest<Category[]>("/categories").then(setCategories).catch((error) => {
      setNotice({ tone: "error", text: errorText(error) });
    });
    return () => window.removeEventListener("popstate", restoreRoute);
  }, []);

  useEffect(() => {
    if (!token) return;
    let active = true;
    setLoading(true);
    Promise.all([
      apiRequest<UserProfile>("/auth/me", token),
      apiRequest<Device[]>("/devices", token),
      apiRequest<Assessment[]>("/assessments/my", token),
      apiRequest<Recovery[]>("/recovery/my", token),
    ]).then(([nextProfile, nextDevices, nextAssessments, nextRecoveries]) => {
      if (!active) return;
      setProfile(nextProfile);
      setDevices(nextDevices);
      setAssessments(nextAssessments);
      setRecoveries(nextRecoveries);
      setSelectedDeviceId((current) => current || nextDevices[0]?.id || "");
    }).catch((error) => {
      if (!active) return;
      setNotice({ tone: "error", text: errorText(error) });
      window.sessionStorage.removeItem("reloop_access_token");
      setToken(null);
      setProfile(null);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [token]);

  useEffect(() => {
    if (!token || window.location.pathname !== "/recommendations" || recommendation || !assessments.length) return;
    let active = true;
    apiRequest<Recommendation>(`/recommendations/device/${assessments[0].device_id}`, token)
      .then((result) => {
        if (!active) return;
        setRecommendation(result);
        setSelectedDeviceId(result.device_id);
        setSelectedRoute(result.recommended_route);
      })
      .catch((error) => { if (active) setNotice({ tone: "error", text: errorText(error) }); });
    return () => { active = false; };
  }, [token, assessments, recommendation]);

  useEffect(() => {
    if (view !== "providers" && view !== "assessment") return;
    let active = true;
    const query = new URLSearchParams();
    if (providerCategory) query.set("category", providerCategory);
    if (cityFilter.trim()) query.set("city", cityFilter.trim());
    if (providerSearch.trim()) query.set("search", providerSearch.trim());
    const suffix = query.toString();
    apiRequest<Provider[]>(`/providers${suffix ? `?${suffix}` : ""}`, token ?? undefined)
      .then((items) => { if (active) setProviders(items); })
      .catch((error) => { if (active) setNotice({ tone: "error", text: errorText(error) }); });
    return () => { active = false; };
  }, [view, providerCategory, cityFilter, providerSearch, token]);

  useEffect(() => {
    if (!token || profile?.role !== "admin") return;
    let active = true;
    Promise.all([
      apiRequest<AdminStats>("/admin/stats", token),
      apiRequest<AdminRequest[]>("/admin/requests", token),
      apiRequest<AdminUser[]>("/admin/users", token),
      apiRequest<AdminAssessment[]>("/admin/assessments", token),
      apiRequest<Provider[]>("/providers", token),
    ]).then(([stats, requests, users, items, nextProviders]) => {
      if (!active) return;
      setAdminStats(stats);
      setAdminRequests(requests);
      setAdminUsers(users);
      setAdminAssessments(items);
      setProviders(nextProviders);
    }).catch((error) => {
      if (active) setNotice({ tone: "error", text: errorText(error) });
    });
    return () => { active = false; };
  }, [token, profile?.role]);

  function showError(error: unknown) {
    setNotice({ tone: "error", text: errorText(error) });
  }

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setNotice(null);
    const data = new FormData(event.currentTarget);
    const endpoint = authMode === "login" ? "/auth/login" : "/auth/register";
    const payload = {
      email: String(data.get("email") ?? "").trim(),
      password: String(data.get("password") ?? ""),
      ...(authMode === "register" ? {
        full_name: String(data.get("full_name") ?? "").trim(),
        city: String(data.get("city") ?? "").trim() || null,
      } : {}),
    };
    try {
      const response = await apiRequest<TokenResponse>(endpoint, undefined, {
        method: "POST", body: JSON.stringify(payload),
      });
      window.sessionStorage.setItem("reloop_access_token", response.access_token);
      setProfile({ id: response.user_id, email: response.email, full_name: response.full_name, role: response.role });
      setToken(response.access_token);
      setView("overview");
      setNotice({ tone: "success", text: `Welcome${response.full_name ? `, ${response.full_name}` : ""}.` });
    } catch (error) {
      showError(error);
    } finally {
      setSaving(false);
    }
  }

  function signOut() {
    window.sessionStorage.removeItem("reloop_access_token");
    setToken(null);
    setProfile(null);
    setRecommendation(null);
    updateView("overview");
    setAuthScreen("landing");
    window.history.pushState({}, "", "/");
    setNotice({ tone: "success", text: "You have been signed out." });
  }

  async function createDevice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    const form = event.currentTarget;
    setSaving(true);
    setNotice(null);
    const data = new FormData(event.currentTarget);
    const powerValue = String(data.get("powers_on"));
    const damageValue = String(data.get("physically_damaged"));
    const payload = {
      category_id: Number(data.get("category_id")),
      name: String(data.get("name") ?? "").trim(),
      brand: String(data.get("brand") ?? "").trim(),
      model: String(data.get("model") ?? "").trim(),
      purchase_year: optionalNumber(data.get("purchase_year")),
      working_condition: String(data.get("working_condition")),
      powers_on: powerValue === "unknown" ? null : powerValue === "true",
      physically_damaged: damageValue === "unknown" ? null : damageValue === "true",
      contains_personal_data: data.get("contains_personal_data") === "on",
    };
    try {
      const device = await apiRequest<Device>("/devices", token, { method: "POST", body: JSON.stringify(payload) });
      setDevices((items) => [device, ...items]);
      setSelectedDeviceId(device.id);
      form.reset();
      setNotice({ tone: "success", text: "Device saved to your account." });
    } catch (error) {
      showError(error);
    } finally {
      setSaving(false);
    }
  }
    async function classifyDeviceImage(file: File) {
  if (!file) return;

  setClassification(null);
  setClassificationError("");

  if (!file.type.startsWith("image/")) {
    setClassificationError("Please select a valid image.");
    return;
  }

  if (file.size > 10 * 1024 * 1024) {
    setClassificationError("Image size must be less than 10 MB.");
    return;
  }

  setClassifying(true);

  const categoryMap: Record<string, string> = {
    "Buffalo HD": "Other",
    "InkReader Energy2074": "Tablet",
    "iPad A1430": "Tablet",
    "MacBookProA1278": "Laptop",
    "MP3Player SPC": "Other",
    "Router Sagem": "Other",
    "Samsung GalaxyA9": "Smartphone",
    "Toshib PortegeM300": "Laptop",
    "Toyota EMU": "Other",
    "Toyota stereoNav EA08": "Other",
    "TV controller Sanyo": "Other",
    "Vaio PCG7164M": "Laptop",
  };

  try {
    const formData = new FormData();
    formData.append("image", file);

    const result = await apiRequest<{
      success: boolean;
      filename: string;
      predicted_category: string;
      confidence: number;
      top_predictions: {
        category: string;
        confidence: number;
      }[];
    }>("/devices/classify-image", undefined, {
      method: "POST",
      body: formData,
    });

    setClassification({
      ...result,
      suggested_app_category:
        categoryMap[result.predicted_category] ?? "Other",
    });

  } catch (error) {
    setClassificationError(errorText(error));
  } finally {
    setClassifying(false);
  }


    try {
      const formData = new FormData();
      formData.append("image", file);

      const result = await apiRequest<ClassificationResult>(
        "/devices/classify-image",
        undefined,
        {
          method: "POST",
          body: formData,
        }
      );

      const categoryMap: Record<string, string> = {
        "Buffalo HD": "Other",
        "InkReader Energy2074": "Tablet",
        "iPad A1430": "Tablet",
        "MacBookProA1278": "Laptop",
        "MP3Player SPC": "Other",
        "Router Sagem": "Other",
        "Samsung GalaxyA9": "Smartphone",
        "Toshib PortegeM300": "Laptop",
        "Toyota EMU": "Other",
        "Toyota stereoNav EA08": "Other",
        "TV controller Sanyo": "Other",
        "Vaio PCG7164M": "Laptop",
      };

      setClassification({
        ...result,
        suggested_app_category:
          categoryMap[result.predicted_category] ?? "Other",
      });
    } catch (error) {
      setClassificationError(errorText(error));
    } finally {
      setClassifying(false);
    }
  }

  async function submitAssessment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setSaving(true);
    setNotice(null);
    const data = new FormData(event.currentTarget);
    const payload = {
      device_id: String(data.get("device_id")),
      overall_condition: String(data.get("overall_condition")),
      functional_status: String(data.get("functional_status")),
      specific_faults: String(data.get("specific_faults") ?? "").split(",").map((fault) => fault.trim()).filter(Boolean),
      estimated_repair_cost: optionalNumber(data.get("estimated_repair_cost")),
      estimated_resale_value: optionalNumber(data.get("estimated_resale_value")),
      estimated_replacement_cost: optionalNumber(data.get("estimated_replacement_cost")),
      expected_remaining_life_years: optionalNumber(data.get("expected_remaining_life_years")),
      notes: String(data.get("notes") ?? "").trim() || null,
    };
    try {
      const result = await apiRequest<Recommendation>("/assessments", token, { method: "POST", body: JSON.stringify(payload) });
      setRecommendation(result);
      setSelectedDeviceId(result.device_id);
      setSelectedRoute(result.recommended_route);
      setProviderCategory(result.recommended_route === "Reuse" ? "" : result.recommended_route);
      setSelectedProviderId("");
      setView("assessment");
      window.history.pushState({}, "", "/recommendations");
      const latestAssessments = await apiRequest<Assessment[]>("/assessments/my", token);
      setAssessments(latestAssessments);
      setNotice({ tone: "success", text: "Assessment saved. Your ranked options are ready." });
    } catch (error) {
      showError(error);
    } finally {
      setSaving(false);
    }
  }

  async function startRecovery() {
    if (!token || !recommendation) return;
    setSaving(true);
    setNotice(null);
    try {
      const request = await apiRequest<Recovery>("/recovery", token, {
        method: "POST",
        body: JSON.stringify({
          device_id: recommendation.device_id,
          assessment_id: recommendation.assessment_id,
          selected_route: selectedRoute,
          provider_id: selectedProviderId || null,
        }),
      });
      setRecoveries((items) => [request, ...items]);
      setView("recovery");
      setNotice({ tone: "success", text: `Recovery request ${request.tracking_code} is now active.` });
    } catch (error) {
      showError(error);
    } finally {
      setSaving(false);
    }
  }

  async function loadAdminData() {
    if (!token || profile?.role !== "admin") return;
    setLoading(true);
    try {
      const [stats, requests, users, items, nextProviders] = await Promise.all([
        apiRequest<AdminStats>("/admin/stats", token),
        apiRequest<AdminRequest[]>("/admin/requests", token),
        apiRequest<AdminUser[]>("/admin/users", token),
        apiRequest<AdminAssessment[]>("/admin/assessments", token),
        apiRequest<Provider[]>("/providers", token),
      ]);
      setAdminStats(stats);
      setAdminRequests(requests);
      setAdminUsers(users);
      setAdminAssessments(items);
      setProviders(nextProviders);
    } catch (error) {
      showError(error);
    } finally {
      setLoading(false);
    }
  }

  async function createProvider(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || profile?.role !== "admin") return;
    const form = event.currentTarget;
    const data = new FormData(form);
    setSaving(true);
    try {
      const provider = await apiRequest<Provider>("/providers", token, {
        method: "POST",
        body: JSON.stringify({
          name: String(data.get("name") ?? "").trim(),
          category: String(data.get("category")),
          address: String(data.get("address") ?? "").trim(),
          city: String(data.get("city") ?? "").trim(),
          contact_email: String(data.get("contact_email") ?? "").trim() || null,
          contact_phone: String(data.get("contact_phone") ?? "").trim() || null,
          website: String(data.get("website") ?? "").trim() || null,
          services_offered: String(data.get("services_offered") ?? "").split(",").map((service) => service.trim()).filter(Boolean),
          is_sample: false,
          is_verified: false,
        }),
      });
      setProviders((items) => [provider, ...items]);
      form.reset();
      setNotice({ tone: "success", text: "Provider record created. Verify its details before users rely on it." });
    } catch (error) {
      showError(error);
    } finally {
      setSaving(false);
    }
  }

  async function advanceRecovery(item: AdminRequest) {
    if (!token) return;
    const currentIndex = recoveryStatuses.indexOf(item.current_status);
    const nextStatus = recoveryStatuses[currentIndex + 1];
    if (!nextStatus) return;
    setSaving(true);
    try {
      await apiRequest(`/recovery/${item.id}/status`, token, {
        method: "PUT", body: JSON.stringify({ status: nextStatus }),
      });
      await loadAdminData();
      setNotice({ tone: "success", text: `Recovery advanced to ${nextStatus}.` });
    } catch (error) {
      showError(error);
    } finally {
      setSaving(false);
    }
  }

  async function toggleProvider(provider: Provider) {
    if (!token) return;
    setSaving(true);
    try {
      await apiRequest(`/admin/providers/${provider.id}/toggle-verify`, token, { method: "POST" });
      const updated = await apiRequest<Provider[]>("/providers", token);
      setProviders(updated);
      setNotice({ tone: "success", text: "Provider verification updated." });
    } catch (error) {
      showError(error);
    } finally {
      setSaving(false);
    }
  }

  if (!token && authScreen === "landing") {
    return (
      <main className="landing-shell">
        <header className="landing-nav">
          <a className="brand-lockup" href="#top"><span className="brand-mark"><Recycle size={22} /></span><span>ReLoop</span></a>
          <nav aria-label="Landing navigation"><a href="#routes">Recovery options</a><a href="#how-it-works">How it works</a><button type="button" className="button button-secondary" onClick={() => openAuth("login")}>Sign in</button></nav>
        </header>
        <section className="landing-hero" id="top">
          <div className="landing-copy"><p className="eyebrow">A CLEARER NEXT STEP FOR YOUR TECH</p><h1>Make more of the devices you already own.</h1><p>ReLoop helps you compare repair, continued use, resale, donation, refurbishment, and authorized recycling with reasons you can actually inspect.</p><div className="landing-actions"><button type="button" className="button button-primary" onClick={() => openAuth("register")}>Create your account<ArrowRight size={17} /></button><a className="landing-secondary-link" href="#how-it-works">See how decisions are made</a></div><div className="landing-proof"><span><ShieldCheck size={15} /> Private device records</span><span><Activity size={15} /> Transparent scoring</span></div></div>
          <div className="landing-visual"><Image src="https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1400&q=85" alt="Electronic circuit board on a repair bench" width={1400} height={1050} priority unoptimized className="landing-photo" /><div className="visual-shade" /><div className="preview-label">THE RECOVERY DECISION</div><div className="preview-panel"><span className="preview-caption"><CheckCircle2 size={14} /> EXAMPLE ASSESSMENT</span><strong>Keep a working device in service.</strong><div className="preview-meter"><span /><span /><span /><span /></div><div className="preview-metrics"><span>Financial<small>35%</small></span><span>Useful life<small>30%</small></span><span>Convenience<small>15%</small></span><span>Reuse<small>20%</small></span></div><small className="preview-note">Illustrative preview · not a saved assessment</small></div></div>
        </section>
        <section className="landing-route-band" id="routes"><div><p className="eyebrow">SIX PRACTICAL OPTIONS</p><h2>One device. A few better possibilities.</h2></div><div className="landing-route-list">{[
          [Wrench, "Repair"], [RefreshCw, "Reuse"], [Package, "Resell"], [UserRound, "Donate"], [Cpu, "Refurbish"], [Recycle, "Authorized recycling"],
        ].map(([Icon, label], index) => {
          const RouteIcon = Icon as LucideIcon;
          return <div className="landing-route" key={String(label)}><span>0{index + 1}</span><RouteIcon size={17} /><strong>{String(label)}</strong></div>;
        })}</div></section>
        <section className="landing-how" id="how-it-works"><div className="how-heading"><p className="eyebrow">A DECISION YOU CONTROL</p><h2>Assess. Compare. Choose.</h2><p>Your estimates and condition notes feed a transparent weighted score. ReLoop shows eligible options and why they rank, then lets you decide whether to create a trackable request.</p><button type="button" className="button button-dark" onClick={() => openAuth("register")}>Start with a device<ArrowRight size={16} /></button></div><div className="how-steps"><div><span>01</span><strong>Record the basics</strong><p>Add the device, condition, age, known faults, and optional cost estimates.</p></div><div><span>02</span><strong>Review the trade-offs</strong><p>See eligibility reasons and scores across finance, useful life, convenience, and reuse.</p></div><div><span>03</span><strong>Keep the next step visible</strong><p>Choose an option, discover providers, and follow status updates in one place.</p></div></div></section>
        <footer className="landing-footer"><a className="brand-lockup" href="#top"><span className="brand-mark"><Recycle size={19} /></span><span>ReLoop</span></a><span>Decision support, not an automatic service booking.</span><button type="button" className="text-button" onClick={() => openAuth("login")}>Sign in<ArrowRight size={14} /></button></footer>
      </main>
    );
  }

  if (!token) {
    return (
      <main className="auth-shell">
        <section className="auth-panel">
          <div className="brand-lockup"><span className="brand-mark"><Recycle size={23} /></span><span>ReLoop</span></div>
          <p className="eyebrow">DEVICE RECOVERY, MADE PRACTICAL</p>
          <h1>{authMode === "login" ? "Welcome back." : "Start with what you have."}</h1>
          <p className="auth-copy">Make a clear next move for the devices you own, from a repair check to an authorized recycling request.</p>
          <div className="auth-tabs" role="tablist" aria-label="Account access">
            <button type="button" className={authMode === "login" ? "selected" : ""} onClick={() => openAuth("login")}>Sign in</button>
            <button type="button" className={authMode === "register" ? "selected" : ""} onClick={() => openAuth("register")}>Create account</button>
          </div>
          <form className="stack-form" onSubmit={submitAuth}>
            {authMode === "register" && <>
              <label>Full name<input name="full_name" minLength={2} autoComplete="name" required /></label>
              <label>City <span className="optional">Optional</span><input name="city" autoComplete="address-level2" /></label>
            </>}
            <label>Email<input name="email" type="email" autoComplete="email" required /></label>
            <label>Password<input name="password" type="password" minLength={authMode === "register" ? 12 : undefined} maxLength={72} autoComplete={authMode === "login" ? "current-password" : "new-password"} required /></label>
            {authMode === "register" && <p className="field-note">Use at least 12 characters. Passwords are never displayed in your account.</p>}
            {notice?.tone === "error" && <p className="inline-error" role="alert"><CircleAlert size={16} />{notice.text}</p>}
            <button className="button button-primary button-wide" type="submit" disabled={saving}>
              {saving ? "Working..." : authMode === "login" ? "Sign in" : "Create account"}<ArrowRight size={17} />
            </button>
          </form>
          <p className="auth-footnote">Service locations are examples until verified by an administrator. ReLoop does not arrange transport or guarantee provider availability.</p>
        </section>
        <aside className="auth-side">
          <div className="orbit orbit-one" /><div className="orbit orbit-two" />
          <div className="auth-side-content">
            <span className="side-index">01 / A BETTER NEXT STEP</span>
            <h2>Keep useful tech in motion.</h2>
            <div className="route-stack">
              {["Repair", "Reuse", "Resell", "Donate", "Refurbish", "Authorized recycling"].map((route, index) => <div className="route-line" key={route}><span>0{index + 1}</span><strong>{route}</strong><ArrowRight size={15} /></div>)}
            </div>
          </div>
          <span className="side-caption">A decision support tool for the devices already in your hands.</span>
        </aside>
      </main>
    );
  }

  const eligibleRoutes = recommendation?.scores.filter((score) => score.is_eligible) ?? [];
  const routeProviders = providers.filter((provider) => provider.category === selectedRoute);
  const nextStatus = (status: string) => recoveryStatuses[recoveryStatuses.indexOf(status) + 1];

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <a className="brand-lockup" href="#overview" onClick={(event) => { event.preventDefault(); setView("overview"); }}><span className="brand-mark"><Recycle size={21} /></span><span>ReLoop</span></a>
        <div className="workspace-label">PERSONAL WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          {navItems.map(({ id, label, icon: Icon }) => <button key={id} type="button" className={`nav-item ${view === id ? "active" : ""}`} onClick={() => {
            setView(id);
            if (id === "providers") { setProviderCategory(""); setCityFilter(""); setProviderSearch(""); }
          }}><Icon size={18} /><span>{label}</span>{id === "recovery" && recoveries.length > 0 && <span className="nav-count">{recoveries.length}</span>}</button>)}
          {profile?.role === "admin" && <button type="button" className={`nav-item ${view === "admin" ? "active" : ""}`} onClick={() => setView("admin")}><ShieldCheck size={18} /><span>Admin</span></button>}
        </nav>
        <div className="sidebar-bottom">
          <div className="privacy-note"><ShieldCheck size={17} /><span>Your device records are private to your account.</span></div>
          <button type="button" className="profile-row" onClick={signOut} title="Sign out"><span className="avatar"><UserRound size={17} /></span><span className="profile-copy"><strong>{profile?.full_name ?? "Account"}</strong><small>{profile?.email}</small></span><LogOut size={16} /></button>
        </div>
      </aside>

      <section className="main-column">
        <header className="topbar">
          <div className="breadcrumbs"><span>ReLoop</span><span className="crumb-divider">/</span><strong>{navItems.find((item) => item.id === view)?.label ?? "Admin"}</strong></div>
          <div className="topbar-right"><span className="api-status"><span /> Connected workspace</span><button type="button" className="icon-button mobile-signout" aria-label="Sign out" onClick={signOut}><LogOut size={17} /></button></div>
        </header>

        {notice && <div className={`notice ${notice.tone}`} role={notice.tone === "error" ? "alert" : "status"}><span>{notice.tone === "success" ? <CheckCircle2 size={17} /> : <CircleAlert size={17} />}{notice.text}</span><button type="button" aria-label="Dismiss message" onClick={() => setNotice(null)}>×</button></div>}

        <div className="content-wrap">
          {loading && <div className="loading-line"><span className="spinner" /> Loading your workspace...</div>}

          {view === "overview" && <>
            <div className="page-heading heading-split"><div><p className="eyebrow">YOUR DEVICE WORKSPACE</p><h1>Good choices start with a clear picture.</h1><p className="heading-copy">Review your devices, compare practical options, and keep recovery requests moving.</p></div><button className="button button-primary" type="button" onClick={() => setView(devices.length ? "assessment" : "devices")}><Plus size={17} />{devices.length ? "Assess a device" : "Add your first device"}</button></div>
            <div className="metric-grid">
              <Metric icon={Package} label="Registered devices" value={devices.length} tone="mint" />
              <Metric icon={ClipboardCheck} label="Assessments" value={assessments.length} tone="orange" />
              <Metric icon={Activity} label="Active recoveries" value={recoveries.filter((item) => item.current_status !== "Completed").length} tone="blue" />
            </div>
            <div className="overview-grid">
              <section className="panel device-panel"><PanelTitle title="Your devices" action="See all" onAction={() => setView("devices")} />
                {devices.length ? <div className="device-list">{devices.slice(0, 4).map((device) => <DeviceRow key={device.id} device={device} onAssess={() => { setSelectedDeviceId(device.id); setView("assessment"); }} />)}</div> : <EmptyState icon={Package} title="No devices registered" copy="Add a device to start an assessment and receive ranked recommendations." action="Add a device" onClick={() => setView("devices")} />}
              </section>
              <section className="panel recent-panel"><PanelTitle title="Recovery in progress" action="Track all" onAction={() => setView("recovery")} />
                {recoveries.length ? <div className="recovery-list compact">{recoveries.slice(0, 3).map((item) => <RecoveryRow key={item.id} item={item} />)}</div> : <EmptyState icon={RefreshCw} title="Nothing in recovery yet" copy="After an assessment, choose an eligible option to create a trackable request." action="Assess a device" onClick={() => setView(devices.length ? "assessment" : "devices")} />}
              </section>
            </div>
            <section className="principle-strip"><div className="principle-icon"><Activity size={21} /></div><div><strong>Recommendations are explainable, not automatic decisions.</strong><p>Scores compare financial feasibility, remaining useful life, convenience, and reuse potential. You choose what happens next.</p></div><span className="weight-chip">35 / 30 / 15 / 20</span></section>
          </>}

          {view === "devices" && <>
            <PageTitle eyebrow="DEVICE INVENTORY" title="Your devices" copy="Keep the basics together. Assessments and recovery records stay linked to each device." />
            <section className="panel form-panel" style={{ marginBottom: "20px" }}>
  <PanelTitle title="Identify your device with AI" />

  <p className="panel-subtitle">
    Upload an electronic-device image to get an AI-powered category prediction.
  </p>

  <input
    type="file"
    accept="image/*"
    disabled={classifying}
    onChange={(event) => {
      const file = event.target.files?.[0];
      if (file) classifyDeviceImage(file);
      event.target.value = "";
    }}
  />

  {classifying && (
    <p className="panel-subtitle">Analyzing image... Please wait.</p>
  )}

  {classificationError && (
    <p style={{ color: "#dc2626", marginTop: "12px" }}>
      {classificationError}
    </p>
  )}

  {classification && (
    <div style={{ marginTop: "16px" }}>
      <h3>
        Predicted device: {classification.predicted_category}
      </h3>

      <p>
        Confidence: {classification.confidence}%
      </p>

      <p>
  Suggested ReLoop category:{" "}
  <strong>{classification.suggested_app_category}</strong>
</p>

      <h4 style={{ marginTop: "12px" }}>Top 3 predictions</h4>

      <ul>
        {classification.top_predictions.map((prediction) => (
          <li key={prediction.category}>
            {prediction.category} — {prediction.confidence}%
          </li>
        ))}
      </ul>

      <p className="panel-subtitle">
        This is an AI suggestion. Verify the category before registering
        your device.
      </p>
    </div>
  )}
</section>
            <div className="two-column-form">
              <section className="panel form-panel"><PanelTitle title="Register a device" /><form className="form-grid" onSubmit={createDevice}>
                <label className="span-two">Device name<input name="name" placeholder="e.g. Work laptop" minLength={2} required /></label>
                <label>Category<select name="category_id" defaultValue="" required><option value="" disabled>Select category</option>{categories.map((category) => <option value={category.id} key={category.id}>{category.name}</option>)}</select></label>
                <label>Brand<input name="brand" placeholder="e.g. Lenovo" required /></label>
                <label>Model<input name="model" placeholder="e.g. ThinkPad T14" required /></label>
                <label>Purchase year<input name="purchase_year" type="number" min="1970" max={new Date().getFullYear()} placeholder="Optional" /></label>
                <label>Current condition<select name="working_condition" defaultValue="unknown"><option value="unknown">Not assessed</option><option value="working">Working</option><option value="minor_issues">Minor issues</option><option value="major_issues">Major issues</option><option value="not_working">Not working</option></select></label>
                <label>Does it power on?<select name="powers_on" defaultValue="unknown"><option value="unknown">Not sure</option><option value="true">Yes</option><option value="false">No</option></select></label>
                <label>Physical damage?<select name="physically_damaged" defaultValue="unknown"><option value="unknown">Not sure</option><option value="false">No</option><option value="true">Yes</option></select></label>
                <label className="checkbox-row span-two"><input name="contains_personal_data" type="checkbox" /><span>It may contain personal data</span></label>
                <button className="button button-primary span-two" type="submit" disabled={saving || !categories.length}>{saving ? "Saving..." : "Save device"}<ArrowRight size={16} /></button>
              </form></section>
              <section className="panel inventory-panel"><PanelTitle title="Registered devices" /><p className="panel-subtitle">{devices.length} saved to your account</p>
                {devices.length ? <div className="device-list">{devices.map((device) => <DeviceRow key={device.id} device={device} onAssess={() => { setSelectedDeviceId(device.id); setView("assessment"); }} />)}</div> : <EmptyState icon={Package} title="Your inventory is empty" copy="Add the first device to begin." />}
              </section>
            </div>
          </>}

          {view === "assessment" && <>
            <PageTitle eyebrow="ASSESSMENT & RECOMMENDATION" title="Find the most useful next step." copy="Describe the condition and faults. ReLoop estimates approximate repair, resale, replacement, and remaining-life ranges." />
            {!devices.length ? <EmptyState icon={Package} title="Add a device first" copy="An assessment needs a saved device to attach the result to." action="Open device inventory" onClick={() => setView("devices")} /> : <>
              <section className="panel assessment-form-panel"><form className="form-grid" onSubmit={submitAssessment}>
                <label className="span-two">Device<select name="device_id" value={selectedDeviceId} onChange={(event) => setSelectedDeviceId(event.target.value)} required>{devices.map((device) => <option value={device.id} key={device.id}>{device.name} · {device.brand} {device.model}</option>)}</select></label>
                <label>Overall condition<select name="overall_condition" defaultValue="good"><option value="excellent">Excellent</option><option value="good">Good</option><option value="fair">Fair</option><option value="poor">Poor</option><option value="unknown">Unknown</option></select></label>
                <label>Functional status<select name="functional_status" defaultValue="fully_functional"><option value="fully_functional">Fully functional</option><option value="partially_functional">Partially functional</option><option value="non_functional">Non-functional</option><option value="unknown">Unknown</option></select></label>
                <label className="span-two">Known faults <span className="optional">Separate with commas</span><input name="specific_faults" placeholder="Battery failure, cracked OLED screen, charging port" /></label>
                <div className="span-two estimate-input-note"><span className="estimate-note-icon"><Activity size={17} /></span><span><strong>ReLoop estimates costs and remaining life for you.</strong><small>Estimates use category, brand/model, age, condition, function, and each reported fault. Mention OLED/LCD or foldable displays when known.</small></span></div>
                <label className="span-two">Notes <span className="optional">Optional</span><textarea name="notes" rows={3} maxLength={2000} placeholder="Anything else that could help explain the condition?" /></label>
                <button className="button button-primary span-two" type="submit" disabled={saving}>{saving ? "Assessing..." : "Save assessment and compare options"}<ArrowRight size={17} /></button>
              </form></section>
              {recommendation && <section className="recommendation-area">
                <div className="result-banner"><div className="result-topline"><span className="result-kicker"><CheckCircle2 size={16} /> RECOMMENDED NEXT STEP</span><span className="score-pill">{recommendation.overall_score.toFixed(1)} / 100</span></div><h2>{recommendation.recommended_route === "Recycle" ? "Authorized recycling" : recommendation.recommended_route}</h2><p>{recommendation.summary}</p><p className="result-explanation">{recommendation.explanation}</p></div>
                {recommendation.financial_summary && <section className="panel estimates-panel"><div className="estimates-heading"><div><p className="eyebrow">DEVICE VALUE ESTIMATES</p><h3>Approximate ranges for your decision</h3></div><span className={`confidence-tag ${recommendation.financial_summary.estimate_confidence ?? "low"}`}>{conditionLabel(recommendation.financial_summary.estimate_confidence ?? "low")} confidence</span></div><div className="estimate-grid"><EstimateTile label="Repair" value={estimateMoneyRange(recommendation.financial_summary.estimated_repair_cost, recommendation.financial_summary.estimate_ranges?.estimated_repair_cost)} detail={`Midpoint ${estimateMoney(recommendation.financial_summary.estimated_repair_cost)}`} source={recommendation.financial_summary.estimate_sources?.estimated_repair_cost} /><EstimateTile label="Replacement" value={estimateMoneyRange(recommendation.financial_summary.estimated_replacement_cost, recommendation.financial_summary.estimate_ranges?.estimated_replacement_cost)} detail={`Midpoint ${estimateMoney(recommendation.financial_summary.estimated_replacement_cost)}`} source={recommendation.financial_summary.estimate_sources?.estimated_replacement_cost} /><EstimateTile label="Resale" value={estimateMoneyRange(recommendation.financial_summary.estimated_resale_value, recommendation.financial_summary.estimate_ranges?.estimated_resale_value)} detail={`Midpoint ${estimateMoney(recommendation.financial_summary.estimated_resale_value)}`} source={recommendation.financial_summary.estimate_sources?.estimated_resale_value} /><EstimateTile label="Remaining life" value={recommendation.financial_summary.estimate_ranges?.expected_remaining_life_years ? `${recommendation.financial_summary.estimate_ranges.expected_remaining_life_years.low.toFixed(1)}–${recommendation.financial_summary.estimate_ranges.expected_remaining_life_years.high.toFixed(1)} years` : recommendation.financial_summary.expected_remaining_life_years == null ? "Unavailable" : `${recommendation.financial_summary.expected_remaining_life_years.toFixed(1)} years`} detail={recommendation.financial_summary.expected_remaining_life_years == null ? undefined : `Midpoint ${recommendation.financial_summary.expected_remaining_life_years.toFixed(1)} years`} source={recommendation.financial_summary.estimate_sources?.expected_remaining_life_years} /></div>{recommendation.financial_summary.matched_faults?.length ? <div className="matched-faults"><span>Matched issues</span>{recommendation.financial_summary.matched_faults.map((fault) => <span className="fault-chip" key={fault}>{conditionLabel(fault)}</span>)}</div> : null}<details className="estimate-method"><summary>Estimation method and assumptions</summary><ul>{recommendation.financial_summary.estimate_notes?.map((note) => <li key={note}>{note}</li>)}</ul></details><p className="estimate-disclaimer">Planning ranges only; not a repair quote, appraisal, or provider offer. Replacement and resale ranges are benchmark estimates.</p></section>}
                <div className="panel score-panel"><PanelTitle title="Eligible options, ranked" /><div className="weight-legend">Weighted comparison: financial 35% · useful life 30% · convenience 15% · reuse 20%</div>
                  <div className="score-table-wrap"><table className="data-table score-table"><thead><tr><th>Option</th><th>Total</th><th>Financial</th><th>Useful life</th><th>Convenience</th><th>Reuse</th></tr></thead><tbody>
                    {recommendation.scores.slice().sort((a, b) => Number(b.is_eligible) - Number(a.is_eligible) || b.final_score - a.final_score).map((score) => <tr key={score.route} className={!score.is_eligible ? "muted-row" : ""}><td><strong>{score.route}</strong>{!score.is_eligible && <small className="table-note">{score.ineligible_reason}</small>}</td><td>{score.is_eligible ? score.final_score.toFixed(1) : "—"}</td><td>{score.is_eligible ? score.financial_score.toFixed(0) : "—"}</td><td>{score.is_eligible ? score.useful_life_score.toFixed(0) : "—"}</td><td>{score.is_eligible ? score.convenience_score.toFixed(0) : "—"}</td><td>{score.is_eligible ? score.reuse_score.toFixed(0) : "—"}</td></tr>)}
                  </tbody></table></div>
                  <p className="provider-disclaimer">Convenience uses a route-level heuristic; provider distance is not included in the score.</p>
                </div>
                <div className="panel recovery-start-panel"><div><span className="eyebrow">YOUR DECISION</span><h3>Choose an eligible option</h3><p>You can select a different eligible route; starting a request does not book a service or arrange transport.</p></div>
                  <div className="recovery-controls"><label>Selected route<select value={selectedRoute} onChange={(event) => { setSelectedRoute(event.target.value); setProviderCategory(event.target.value === "Reuse" ? "" : event.target.value); setSelectedProviderId(""); }}><option value="" disabled>Choose an eligible option</option>{eligibleRoutes.map((score) => <option key={score.route} value={score.route}>{score.route} · {score.final_score.toFixed(1)}</option>)}</select></label>
                    {selectedRoute && selectedRoute !== "Reuse" && <label>Service provider <span className="optional">Optional</span><select value={selectedProviderId} onChange={(event) => setSelectedProviderId(event.target.value)}><option value="">No provider selected</option>{routeProviders.map((provider) => <option value={provider.id} key={provider.id}>{provider.name}{provider.is_sample ? " · sample" : ""}</option>)}</select></label>}
                    <button className="button button-dark" type="button" onClick={startRecovery} disabled={saving || !selectedRoute}>{saving ? "Starting..." : "Create recovery request"}<ArrowRight size={16} /></button>
                  </div>
                </div>
              </section>}
            </>}
          </>}

          {view === "providers" && <>
            <PageTitle eyebrow="SERVICE DIRECTORY" title="Find a suitable provider." copy="Filter the provider records currently in ReLoop. Sample listings are clearly marked and are not verified businesses." />
            <section className="panel provider-filter-panel"><div className="filter-grid"><label>Recovery option<select value={providerCategory} onChange={(event) => setProviderCategory(event.target.value)}><option value="">All options</option>{["Repair", "Resell", "Donate", "Refurbish", "Recycle"].map((route) => <option key={route}>{route}</option>)}</select></label><label>City<input value={cityFilter} onChange={(event) => setCityFilter(event.target.value)} placeholder="Search by city" /></label><label className="search-field">Provider or service<Search size={16} /><input value={providerSearch} onChange={(event) => setProviderSearch(event.target.value)} placeholder="Name, location, service" /></label></div></section>
            <div className="provider-summary"><span>{providers.length} matching providers</span><span><BadgeCheck size={15} /> Verified status is shown on each listing</span></div>
            {providers.length ? <div className="provider-grid">{providers.map((provider) => <ProviderCard key={provider.id} provider={provider} admin={profile?.role === "admin"} saving={saving} onToggle={() => toggleProvider(provider)} />)}</div> : <EmptyState icon={MapPin} title="No providers match these filters" copy="Try another city or clear the selected option." action="Clear filters" onClick={() => { setProviderCategory(""); setCityFilter(""); setProviderSearch(""); }} />}
          </>}

          {view === "recovery" && <>
            <PageTitle eyebrow="RECOVERY TRACKING" title="Keep every request in view." copy="Track status updates recorded by the ReLoop team. Your tracking details are private to your account." />
            {recoveries.length ? <div className="recovery-list">{recoveries.map((item) => <RecoveryCard key={item.id} item={item} />)}</div> : <EmptyState icon={RefreshCw} title="No recovery requests yet" copy="Submit an assessment, choose an eligible route, and create a request to begin tracking." action={devices.length ? "Assess a device" : "Register a device"} onClick={() => setView(devices.length ? "assessment" : "devices")} />}
          </>}

          {view === "admin" && profile?.role === "admin" && <>
            <div className="page-heading heading-split"><div><p className="eyebrow">OPERATIONS</p><h1>Admin overview</h1><p className="heading-copy">Live account, assessment, provider, and recovery data from the ReLoop API.</p></div><button className="button button-secondary" type="button" onClick={loadAdminData} disabled={loading}><RefreshCw size={16} /> Refresh data</button></div>
            {adminStats ? <>
              <div className="admin-metrics">{Object.entries(adminStats.kpis).map(([key, value]) => <Metric key={key} icon={Activity} label={conditionLabel(key.replace("total_", "").replaceAll("_", " "))} value={value} tone="mint" />)}</div>
              <div className="admin-grid">
                <section className="panel admin-panel"><PanelTitle title="Recommendations by route" /><div className="route-counts">{adminStats.recommendations_by_route.map((item) => <div className="route-count-row" key={item.route}><span>{item.route}</span><strong>{item.count}</strong></div>)}</div></section>
                <section className="panel admin-panel"><PanelTitle title="Recovery status totals" /><div className="route-counts">{adminStats.recovery_by_status.filter((item) => item.count > 0).map((item) => <div className="route-count-row" key={item.status}><span>{item.status}</span><strong>{item.count}</strong></div>)}{adminStats.recovery_by_status.every((item) => item.count === 0) && <p className="empty-inline">No recovery activity yet.</p>}</div></section>
              </div>
              <section className="panel admin-panel"><PanelTitle title="Recovery queue" /><div className="table-scroll"><table className="data-table"><thead><tr><th>Tracking code</th><th>Customer</th><th>Device</th><th>Option</th><th>Status</th><th>Next action</th></tr></thead><tbody>{adminRequests.map((item) => <tr key={item.id}><td><strong>{item.tracking_code}</strong></td><td>{item.user_name}<small className="table-note">{item.user_email}</small></td><td>{item.device_name}</td><td>{item.selected_route}</td><td><StatusTag status={item.current_status} /></td><td>{nextStatus(item.current_status) ? <button className="button button-small button-secondary" type="button" disabled={saving} onClick={() => advanceRecovery(item)}>Advance</button> : <span className="completed-label">Complete</span>}</td></tr>)}</tbody></table>{!adminRequests.length && <p className="empty-inline">No recovery requests have been created.</p>}</div></section>
              <div className="admin-grid">
                <section className="panel admin-panel"><PanelTitle title="Recent assessments" /><div className="table-scroll"><table className="data-table"><thead><tr><th>Device</th><th>Owner</th><th>Condition</th><th>Recommendation</th><th>Score</th></tr></thead><tbody>{adminAssessments.slice(0, 8).map((item) => <tr key={item.id}><td>{item.device_name}<small className="table-note">{item.category}</small></td><td>{item.user_email}</td><td>{conditionLabel(item.overall_condition)}</td><td>{item.recommended_route}</td><td>{item.overall_score?.toFixed(1) ?? "—"}</td></tr>)}</tbody></table></div></section>
                <section className="panel admin-panel"><PanelTitle title="Accounts" /><div className="table-scroll"><table className="data-table"><thead><tr><th>Name</th><th>Role</th><th>Devices</th><th>Assessments</th></tr></thead><tbody>{adminUsers.slice(0, 10).map((item) => <tr key={item.id}><td>{item.full_name}<small className="table-note">{item.email}</small></td><td><span className="role-tag">{item.role}</span></td><td>{item.device_count}</td><td>{item.assessment_count}</td></tr>)}</tbody></table></div></section>
              </div>
              <section className="panel admin-panel"><PanelTitle title="Add a provider" /><form className="form-grid admin-provider-form" onSubmit={createProvider}>
                <label>Provider name<input name="name" minLength={2} required /></label><label>Category<select name="category" defaultValue="Repair">{["Repair", "Resell", "Donate", "Refurbish", "Recycle"].map((route) => <option key={route}>{route}</option>)}</select></label>
                <label className="span-two">Address<input name="address" required /></label><label>City<input name="city" required /></label><label>Contact email<input name="contact_email" type="email" /></label>
                <label>Contact phone<input name="contact_phone" type="tel" /></label><label>Website<input name="website" type="url" placeholder="https://" /></label>
                <label className="span-two">Services <span className="optional">Separate with commas</span><input name="services_offered" /></label>
                <button className="button button-primary span-two" type="submit" disabled={saving}>{saving ? "Saving..." : "Create provider record"}<ArrowRight size={16} /></button>
              </form></section>
              <section className="panel admin-panel"><PanelTitle title="Provider records" /><div className="table-scroll"><table className="data-table"><thead><tr><th>Provider</th><th>Category</th><th>City</th><th>Record</th><th>Verification</th><th>Action</th></tr></thead><tbody>{providers.map((provider) => <tr key={provider.id}><td>{provider.name}</td><td>{provider.category}</td><td>{provider.city}</td><td>{provider.is_sample ? "Sample" : "Provider"}</td><td>{provider.is_verified ? "Verified" : "Unverified"}</td><td>{provider.is_sample ? <span className="completed-label">Sample data</span> : <button className="button button-small button-secondary" type="button" disabled={saving} onClick={() => toggleProvider(provider)}>{provider.is_verified ? "Unverify" : "Verify"}</button>}</td></tr>)}</tbody></table></div></section>
            </> : <EmptyState icon={ShieldCheck} title="Loading operational data" copy="Admin access is verified by the backend. Refresh if the data does not appear." action="Load data" onClick={loadAdminData} />}
          </>}

          {view === "admin" && profile?.role !== "admin" && <EmptyState icon={ShieldCheck} title="Admin access required" copy="This area is available only to accounts provisioned as administrators." />}
        </div>
        <footer className="footer-line"><span>ReLoop · Device decision support</span><span>Recommendations are guidance; final decisions remain yours.</span></footer>
      </section>
    </main>
  );
}

function PageTitle({ eyebrow, title, copy }: { eyebrow: string; title: string; copy: string }) {
  return <div className="page-heading"><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="heading-copy">{copy}</p></div>;
}

function PanelTitle({ title, action, onAction }: { title: string; action?: string; onAction?: () => void }) {
  return <div className="panel-heading"><h2>{title}</h2>{action && onAction && <button type="button" className="text-button" onClick={onAction}>{action}<ArrowRight size={15} /></button>}</div>;
}

function Metric({ icon: Icon, label, value, tone }: { icon: LucideIcon; label: string; value: number; tone: string }) {
  return <div className={`metric-card ${tone}`}><span className="metric-icon"><Icon size={18} /></span><span className="metric-label">{label}</span><strong>{value}</strong></div>;
}

function EstimateTile({ label, value, detail, source }: { label: string; value: string; detail?: string; source?: string }) {
  return <div className="estimate-tile"><span>{label}</span><strong>{value}</strong>{detail && <small>{detail}</small>}<small>{source ?? "ReLoop estimate"}</small></div>;
}

function EmptyState({ icon: Icon, title, copy, action, onClick }: { icon: LucideIcon; title: string; copy: string; action?: string; onClick?: () => void }) {
  return <div className="empty-state"><span className="empty-icon"><Icon size={20} /></span><h3>{title}</h3><p>{copy}</p>{action && onClick && <button type="button" className="button button-secondary" onClick={onClick}>{action}<ArrowRight size={15} /></button>}</div>;
}

function DeviceRow({ device, onAssess }: { device: Device; onAssess: () => void }) {
  const Icon = device.category_name === "Smartphone" ? Smartphone : device.category_name === "Tablet" ? Tablet : device.category_name === "Monitor" ? Monitor : device.category_name === "Laptop" ? Cpu : Package;
  return <div className="device-row"><span className="device-icon"><Icon size={19} /></span><div className="row-main"><strong>{device.name}</strong><span>{device.brand} {device.model} · {device.category_name ?? "Device"}</span></div><span className={`condition-tag ${device.working_condition}`}>{conditionLabel(device.working_condition)}</span><button type="button" className="icon-button row-action" aria-label={`Assess ${device.name}`} onClick={onAssess}><ArrowRight size={16} /></button></div>;
}

function ProviderCard({ provider, admin, saving, onToggle }: { provider: Provider; admin: boolean; saving: boolean; onToggle: () => void }) {
  return <article className="provider-card"><div className="provider-card-head"><span className="provider-glyph"><MapPin size={19} /></span><div><h3>{provider.name}</h3><span className="provider-meta">{provider.category} · {provider.city}</span></div></div><p className="provider-address">{provider.address}</p><div className="provider-badges">{provider.is_verified ? <span className="verified-badge"><BadgeCheck size={14} /> Verified</span> : <span className="unverified-badge"><CircleAlert size={14} /> Not verified</span>}{provider.is_sample && <span className="sample-badge">Sample listing</span>}</div>
    {provider.services_offered?.length > 0 && <div className="service-chips">{provider.services_offered.slice(0, 4).map((service) => <span key={service}>{service}</span>)}</div>}
    <div className="provider-card-foot"><div className="provider-contact">{provider.contact_phone && <span>{provider.contact_phone}</span>}{provider.website && <a href={provider.website} target="_blank" rel="noreferrer">Website <ArrowRight size={13} /></a>}</div>{admin && !provider.is_sample && <button className="button button-small button-secondary" type="button" disabled={saving} onClick={onToggle}>{provider.is_verified ? "Unverify" : "Verify"}</button>}</div>
  </article>;
}

function StatusTag({ status }: { status: string }) {
  return <span className={`status-tag ${status === "Completed" ? "done" : "active"}`}><span />{status}</span>;
}

function RecoveryRow({ item }: { item: Recovery }) {
  return <div className="recovery-row"><span className="timeline-icon"><Clock3 size={16} /></span><div className="row-main"><strong>{item.device_name ?? "Device"} · {item.selected_route}</strong><span>{item.tracking_code} · {item.provider_name ?? "Provider not selected"}</span></div><StatusTag status={item.current_status} /></div>;
}

function RecoveryCard({ item }: { item: Recovery }) {
  return <article className="panel recovery-card"><div className="recovery-card-head"><div><p className="eyebrow">{item.tracking_code}</p><h2>{item.device_name ?? "Device"}</h2><span className="recovery-subtitle">{item.device_category ?? "Electronics"} · {item.selected_route} · {item.provider_name ?? "No provider selected"}</span></div><StatusTag status={item.current_status} /></div><div className="status-timeline">{recoveryStatuses.map((status, index) => {
    const current = recoveryStatuses.indexOf(item.current_status);
    const reached = index <= current;
    const timestamp = item.status_history.find((entry) => entry.status === status)?.created_at;
    return <div className={`timeline-step ${reached ? "reached" : ""}`} key={status}><span className="timeline-dot">{reached ? <CheckCircle2 size={15} /> : index + 1}</span><div><strong>{status}</strong>{timestamp && <small>{new Date(timestamp).toISOString().slice(0, 16).replace("T", " ")}</small>}</div></div>;
  })}</div></article>;
}
