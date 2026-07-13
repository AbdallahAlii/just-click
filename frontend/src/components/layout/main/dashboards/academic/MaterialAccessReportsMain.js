"use client";

import AdminDashboardPage, {
  AdminMetricCard,
  AdminReportCard,
  AdminReportRow,
  AdminSkeletonBlock,
} from "@/components/shared/dashboards/AdminDashboardPage";
import { useMaterialAccessReports } from "@/features/materials/hooks";
import { BarChart3, Download, Eye, Users } from "lucide-react";
import Link from "next/link";

const EMPTY = {
  views: "No material views have been recorded yet.",
  downloads: "No material downloads have been recorded yet.",
  courses: "No course engagement has been recorded yet.",
  least: "No materials to rank yet.",
};

export default function MaterialAccessReportsMain() {
  const { data, isLoading, isError, refetch } = useMaterialAccessReports({
    limit: 10,
  });
  const report = data?.data || {};
  const summary = report.summary || {};

  const feedbackLink = (
    <Link
      href="/admin/dashboards/admin-academic/materials/feedback"
      className="inline-flex items-center justify-center w-full sm:w-auto px-4 py-2.5 rounded-xl text-sm font-semibold text-ds-action border border-ds-border bg-ds-surface hover:bg-ds-surface-hover transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-focus"
    >
      View student feedback
    </Link>
  );

  if (isError) {
    return (
      <AdminDashboardPage
        title="Material Access Reports"
        description="Views, downloads, course access, and student engagement."
        action={feedbackLink}
      >
        <div
          className="rounded-2xl border border-ds-error/30 bg-ds-surface p-8 text-center"
          role="alert"
        >
          <p className="text-ds-error font-medium">
            Failed to load material access reports.
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-4 px-4 py-2 rounded-xl bg-ds-action text-white text-sm font-semibold hover:bg-ds-action-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-ds-focus"
          >
            Try again
          </button>
        </div>
      </AdminDashboardPage>
    );
  }

  return (
    <AdminDashboardPage
      title="Material Access Reports"
      description="Views, downloads, course access, and student engagement from tracked material interactions."
      action={feedbackLink}
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {isLoading ? (
          [...Array(4)].map((_, i) => (
            <div
              key={i}
              className="h-28 rounded-2xl bg-ds-surface-secondary animate-pulse"
              aria-hidden="true"
            />
          ))
        ) : (
          <>
            <AdminMetricCard
              label="Total materials"
              value={summary.total_materials ?? 0}
              icon={BarChart3}
            />
            <AdminMetricCard
              label="Total views"
              value={summary.total_views ?? 0}
              icon={Eye}
            />
            <AdminMetricCard
              label="Total downloads"
              value={summary.total_downloads ?? 0}
              icon={Download}
            />
            <AdminMetricCard
              label="Engaged students"
              value={summary.engaged_students ?? 0}
              hint={`${summary.materials_without_access ?? 0} materials with no access yet`}
              icon={Users}
            />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 sm:gap-6">
        <AdminReportCard
          title="Most viewed materials"
          isEmpty={!isLoading && !report.top_viewed_materials?.length}
          emptyMessage={EMPTY.views}
        >
          {isLoading ? (
            <AdminSkeletonBlock />
          ) : (
            report.top_viewed_materials?.map((row) => (
              <AdminReportRow
                key={row.material_id}
                primary={row.title}
                secondary={
                  row.course?.code
                    ? `${row.course.code}${row.course?.title ? ` · ${row.course.title}` : ""}`
                    : null
                }
                meta={`${row.view_count} views`}
              />
            ))
          )}
        </AdminReportCard>

        <AdminReportCard
          title="Most downloaded materials"
          isEmpty={!isLoading && !report.top_downloaded_materials?.length}
          emptyMessage={EMPTY.downloads}
        >
          {isLoading ? (
            <AdminSkeletonBlock />
          ) : (
            report.top_downloaded_materials?.map((row) => (
              <AdminReportRow
                key={row.material_id}
                primary={row.title}
                secondary={
                  row.course?.code
                    ? `${row.course.code}${row.course?.title ? ` · ${row.course.title}` : ""}`
                    : null
                }
                meta={`${row.download_count} downloads`}
              />
            ))
          )}
        </AdminReportCard>

        <AdminReportCard
          title="Materials with lowest engagement"
          isEmpty={!isLoading && !report.least_accessed_materials?.length}
          emptyMessage={EMPTY.least}
        >
          {isLoading ? (
            <AdminSkeletonBlock lines={5} />
          ) : (
            report.least_accessed_materials?.map((row) => (
              <AdminReportRow
                key={row.material_id}
                primary={row.title}
                secondary={
                  row.course?.code
                    ? `${row.course.code}${row.course?.title ? ` · ${row.course.title}` : ""}`
                    : null
                }
                meta={`${row.view_count} views · ${row.download_count} downloads`}
              />
            ))
          )}
        </AdminReportCard>

        <AdminReportCard
          title="Most accessed courses"
          isEmpty={!isLoading && !report.most_accessed_courses?.length}
          emptyMessage={EMPTY.courses}
        >
          {isLoading ? (
            <AdminSkeletonBlock />
          ) : (
            report.most_accessed_courses?.map((row) => (
              <AdminReportRow
                key={row.course_id}
                primary={row.title}
                secondary={row.code || null}
                meta={`${row.view_count} views · ${row.download_count} downloads`}
              />
            ))
          )}
        </AdminReportCard>
      </div>
    </AdminDashboardPage>
  );
}
