import ContactMessagesAdminMain from "@/components/layout/main/dashboards/academic/ContactMessagesAdminMain";
import DashboardContainer from "@/components/shared/containers/DashboardContainer";
import ThemeController from "@/components/shared/others/ThemeController";
import DsahboardWrapper from "@/components/shared/wrappers/DsahboardWrapper";

export const metadata = {
  title: "Contact Messages | Admin Dashboard",
  description: "Review and handle Contact Us messages",
};

export default function ContactMessagesAdminPage() {
  return (
    <main>
      <DsahboardWrapper>
        <DashboardContainer>
          <ContactMessagesAdminMain />
        </DashboardContainer>
      </DsahboardWrapper>
      <ThemeController />
    </main>
  );
}
