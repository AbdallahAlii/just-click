"use client";

import {
  Activity,
  BookOpen,
  Download,
  Eye,
  FileSpreadsheet,
  FileText,
  GraduationCap,
  Image as ImageIcon,
  MessageSquareWarning,
  Presentation,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  UserCog,
  UserPlus,
  Users,
  Video,
} from "lucide-react";

import { useAdminDashboardSummary } from "@/features/dashboard/hooks";
import { useMaterialFeedbackAdminSummary } from "@/features/materials/hooks";
import Link from "next/link";

const Card = ({ title, value, change, trend, icon: Icon, meta, metaIcons }) => {
  return (
    <div className="bg-ds-surface border border-ds-border rounded-3xl p-6 shadow-sm hover:shadow-lg hover:border-ds-border transition-all duration-300 relative overflow-hidden group">
      <div className="absolute -top-10 -right-10 w-32 h-32 bg-gradient-to-br from-ds-action/5 to-purple-500/5 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-500"></div>

      <div className="flex justify-between items-start mb-6 relative z-10">
        <div className="p-3 bg-ds-surface-hover rounded-2xl text-ds-text-secondary border border-ds-border group-hover:scale-110 group-hover:bg-ds-action/10 group-hover:text-ds-action transition-all duration-300">
          <Icon className="w-6 h-6 stroke-[1.5]" />
        </div>
        <div
          className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${
            trend === "up"
              ? "bg-emerald-50 text-emerald-700"
              : "bg-rose-50 text-rose-700"
          }`}
        >
          {trend === "up" ? (
            <TrendingUp className="w-3.5 h-3.5" />
          ) : (
            <TrendingDown className="w-3.5 h-3.5" />
          )}
          <span>{change}%</span>
        </div>
      </div>

      <div className="relative z-10 mb-6">
        <h3 className="text-ds-text-secondary text-sm font-medium mb-2">
          {title}
        </h3>
        <p className="text-4xl font-bold tracking-tight text-ds-text-primary">
          {value.toLocaleString()}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-2 mt-2 relative z-10 pt-4 border-t border-ds-border">
        {Object.entries(meta)
          .slice(0, 3)
          .map(([key, val], idx) => {
            if (typeof val !== "number") return null;
            const MetaIcon = metaIcons[key] || Activity;
            return (
              <div
                key={key}
                className="flex flex-col items-start p-2 rounded-xl bg-ds-surface-hover"
              >
                <span className="flex items-center gap-1.5 text-xs text-ds-text-secondary capitalize mb-1">
                  <MetaIcon className="w-3 h-3" />
                  <span className="truncate w-12">{key}</span>
                </span>
                <span className="text-sm font-semibold text-ds-text-primary">
                  {val.toLocaleString()}
                </span>
              </div>
            );
          })}
      </div>
    </div>
  );
};

const UserGrowthChart = ({ data }) => {
  const maxUsers = Math.max(...data.map((d) => d.new_users));

  return (
    <div className="bg-ds-surface border border-ds-border rounded-3xl p-6 shadow-sm relative overflow-hidden h-full flex flex-col">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h2 className="text-lg font-bold text-ds-text-primary">
            User Growth
          </h2>
          <p className="text-sm text-ds-text-secondary mt-1">
            Monthly registration trends
          </p>
        </div>
        <div className="p-2 bg-ds-surface-hover rounded-lg">
          <Activity className="w-5 h-5 text-ds-text-secondary" />
        </div>
      </div>

      <div className="flex-1 flex items-end justify-between px-4 pb-2 pt-6 gap-4">
        {data.map((item, idx) => {
          const heightPercent =
            maxUsers > 0 ? (item.new_users / maxUsers) * 100 : 0;
          return (
            <div key={idx} className="flex flex-col items-center flex-1 group">
              <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 mb-2 bg-ds-surface text-ds-text-primary text-xs py-1.5 px-3 rounded-lg shadow-lg whitespace-nowrap z-10 relative">
                <span className="font-bold">{item.new_users} total</span>
                <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 border-default border-t-ds-surface border-x-transparent border-b-transparent border-t-4 border-x-4 border-b-0"></div>
              </div>

              <div className="w-full max-w-[40px] bg-ds-surface-hover rounded-t-xl relative overflow-hidden h-40 flex items-end">
                <div
                  className="w-full bg-ds-action rounded-t-xl transition-all duration-1000 ease-out group-hover:bg-ds-action-hover"
                  style={{ height: `${heightPercent}%` }}
                >
                  <div className="absolute inset-x-0 top-0 h-2 bg-white/20 rounded-t-xl"></div>
                </div>
              </div>

              <span className="mt-4 text-sm font-medium text-ds-text-secondary">
                {item.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const MaterialBreakdown = ({ data }) => {
  const total = Object.values(data).reduce(
    (acc, val) => acc + (typeof val === "number" ? val : 0),
    0,
  );

  const icons = {
    pdf: { icon: FileText, color: "bg-red-500" },
    ppt: { icon: Presentation, color: "bg-orange-500" },
    slides: { icon: Presentation, color: "bg-orange-500" },
    doc: { icon: FileSpreadsheet, color: "bg-blue-500" },
    image: { icon: ImageIcon, color: "bg-emerald-500" },
    video: { icon: Video, color: "bg-purple-500" },
    link: { icon: Activity, color: "bg-cyan-500" },
    other: { icon: BookOpen, color: "bg-slate-500" },
  };

  return (
    <div className="bg-ds-surface border border-ds-border rounded-3xl p-6 shadow-sm h-full flex flex-col">
      <div className="mb-6">
        <h2 className="text-lg font-bold text-ds-text-primary">
          Material Composition
        </h2>
        <p className="text-sm text-ds-text-secondary mt-1">
          Distribution across formats
        </p>
      </div>

      <div className="flex-1 flex flex-col justify-center space-y-5">
        {Object.entries(data).map(([key, val]) => {
          if (typeof val !== "number") return null;
          const { icon: Icon, color } = icons[key] || {
            icon: BookOpen,
            color: "bg-slate-500",
          };
          const percent = total > 0 ? ((val / total) * 100).toFixed(1) : 0;

          return (
            <div key={key} className="flex items-center gap-4 group">
              <div
                className={`p-2.5 rounded-xl text-white ${color} shadow-sm group-hover:scale-110 transition-transform`}
              >
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-sm font-semibold text-ds-text-primary capitalize">
                    {key}
                  </span>
                  <span className="text-sm font-medium text-ds-text-secondary">
                    {val} ({percent}%)
                  </span>
                </div>
                <div className="h-2 w-full bg-ds-surface-hover rounded-full overflow-hidden">
                  <div
                    className={`h-full ${color} rounded-full transition-all duration-1000 ease-out`}
                    style={{ width: `${percent}%` }}
                  ></div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const AdminDashboardMain = () => {
  const { data: apiResponse, isLoading, isError } = useAdminDashboardSummary();
  const { data: feedbackSummaryRes } = useMaterialFeedbackAdminSummary();
  const feedbackSummary = feedbackSummaryRes?.data || {};

  if (isLoading) {
    return (
      <div className="p-10 text-center text-ds-text-secondary animate-pulse">
        Loading dashboard summary...
      </div>
    );
  }
  if (isError || !apiResponse?.data) {
    return (
      <div className="p-10 text-center text-ds-error">
        Failed to load dashboard data.
      </div>
    );
  }

  const { summary_cards, charts } = apiResponse.data;
  const meta = apiResponse.meta || { generated_at: new Date().toISOString() };

  const metaIcons = {
    student_count: GraduationCap,
    lecturers: UserCog,
    admin_count: ShieldCheck,
    total_views: Eye,
    total_downloads: Download,
    pdf: FileText,
    ppt: Presentation,
    doc: FileSpreadsheet,
    image: ImageIcon,
    video: Video,
  };

  return (
    <div className="w-full max-w-screen-2xl mx-auto pb-10 space-y-8 animate-fade-in">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 py-4">
        <div>
          <h1 className="text-3xl font-bold text-ds-text-primary mb-2 font-display tracking-tight">
            Dashboard Overview
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <button className="px-4 py-2 bg-ds-surface border border-ds-border text-ds-text-secondary rounded-xl text-sm font-medium hover:bg-ds-surface-hover transition-colors shadow-sm flex items-center gap-2">
            <Download className="w-4 h-4" />
            Export Report
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        <Card
          title="Total Users"
          value={summary_cards.total_users.value}
          change={summary_cards.total_users.change_percent}
          trend={summary_cards.total_users.trend}
          icon={Users}
          meta={Object.fromEntries(
            Object.entries(summary_cards.total_users.meta || {}).filter(
              ([key]) => !["staff", "lecturers"].includes(key),
            ),
          )}
          metaIcons={metaIcons}
        />
        <Card
          title="Pending Approvals"
          value={summary_cards.pending_user_approvals.value}
          change={summary_cards.pending_user_approvals.change_percent}
          trend={summary_cards.pending_user_approvals.trend}
          icon={UserPlus}
          meta={summary_cards.pending_user_approvals.meta}
          metaIcons={metaIcons}
        />
        <Card
          title="Total Materials"
          value={summary_cards.total_materials.value}
          change={summary_cards.total_materials.change_percent}
          trend={summary_cards.total_materials.trend}
          icon={BookOpen}
          meta={summary_cards.total_materials.meta}
          metaIcons={metaIcons}
        />
        <Card
          title="Material Analytics"
          value={summary_cards.global_material_analytics.value}
          change={summary_cards.global_material_analytics.change_percent}
          trend={summary_cards.global_material_analytics.trend}
          icon={Activity}
          meta={summary_cards.global_material_analytics.meta}
          metaIcons={metaIcons}
        />
      </div>

      {/* Charts & Graphics Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <UserGrowthChart data={charts.user_growth} />
        </div>
        <div className="lg:col-span-1">
          <MaterialBreakdown data={summary_cards.total_materials.meta} />
        </div>
      </div>

      {/* Material feedback moderation */}
      <div className="bg-ds-surface border border-ds-border rounded-3xl overflow-hidden shadow-sm">
        <div className="px-6 py-5 border-b border-ds-border flex flex-wrap justify-between items-center gap-3 bg-ds-surface-hover">
          <div>
            <h2 className="text-lg font-bold text-ds-text-primary">
              Material Feedback Inbox
            </h2>
            <p className="text-sm text-ds-text-secondary mt-1">
              Student comments, questions, and broken-file reports
            </p>
          </div>
          <Link
            href="/admin/dashboards/admin-academic/materials/feedback"
            className="text-sm font-semibold text-primaryColor hover:underline"
          >
            Open inbox →
          </Link>
        </div>
        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-5 rounded-2xl border border-amber-100 bg-amber-50/50 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-amber-100 text-amber-700 rounded-xl">
                <MessageSquareWarning className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-ds-text-primary">
                  Open issues
                </h4>
                <p className="text-xs text-ds-text-secondary">
                  Needs admin action
                </p>
              </div>
            </div>
            <div className="text-2xl font-bold text-ds-text-primary">
              {feedbackSummary.open_issues ?? 0}
            </div>
          </div>
          <div className="p-5 rounded-2xl border border-ds-border bg-ds-surface-hover flex items-center justify-between">
            <div>
              <h4 className="text-sm font-semibold text-ds-text-primary">
                Awaiting reply
              </h4>
              <p className="text-xs text-ds-text-secondary">
                No admin response yet
              </p>
            </div>
            <div className="text-2xl font-bold text-ds-text-primary">
              {feedbackSummary.awaiting_admin_reply ?? 0}
            </div>
          </div>
          <div className="p-5 rounded-2xl border border-ds-border bg-ds-surface-hover flex items-center justify-between">
            <div>
              <h4 className="text-sm font-semibold text-ds-text-primary">
                Broken files
              </h4>
              <p className="text-xs text-ds-text-secondary">
                Open reports
              </p>
            </div>
            <div className="text-2xl font-bold text-ds-text-primary">
              {feedbackSummary.broken_file_open ?? 0}
            </div>
          </div>
          <div className="p-5 rounded-2xl border border-ds-border bg-ds-surface-hover flex items-center justify-between">
            <div>
              <h4 className="text-sm font-semibold text-ds-text-primary">
                Comments
              </h4>
              <p className="text-xs text-ds-text-secondary">
                All time
              </p>
            </div>
            <div className="text-2xl font-bold text-ds-text-primary">
              {feedbackSummary.comments_total ?? 0}
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Approvals Section */}
      <div className="bg-ds-surface border border-ds-border rounded-3xl overflow-hidden shadow-sm">
        <div className="px-6 py-5 border-b border-ds-border flex justify-between items-center bg-ds-surface-hover">
          <h2 className="text-lg font-bold text-ds-text-primary">
            Action Required: Approvals
          </h2>
          <span className="bg-ds-error/10 text-ds-error py-1 px-3 rounded-full text-xs font-bold">
            {summary_cards.pending_user_approvals.value} Pending
          </span>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-5 rounded-2xl border border-ds-border bg-ds-surface-hover flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-orange-100 text-orange-600 rounded-xl">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-ds-text-primary">
                    Admin Approvals
                  </h4>
                  <p className="text-xs text-ds-text-secondary mt-0.5">
                    Awaiting super admin review
                  </p>
                </div>
              </div>
              <div className="text-2xl font-bold text-ds-text-primary">
                {
                  summary_cards.pending_user_approvals.meta.approval_stages
                    .pending_admin_approval
                }
              </div>
            </div>

            <div className="p-5 rounded-2xl border border-ds-border bg-ds-surface-hover flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-100 text-blue-600 rounded-xl">
                  <Users className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-ds-text-primary">
                    Email Verifications
                  </h4>
                  <p className="text-xs text-ds-text-secondary mt-0.5">
                    Users pending email verification
                  </p>
                </div>
              </div>
              <div className="text-2xl font-bold text-ds-text-primary">
                {
                  summary_cards.pending_user_approvals.meta.approval_stages
                    .pending_email_verification
                }
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboardMain;
