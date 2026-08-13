import AuthGate from "@/components/AuthGate";
import Footer from "@/components/layout/footer/Footer";
import DashboardHeader from "@/components/layout/header/DashboardHeader";
import Scrollup from "@/components/shared/others/Scrollup";

export default function ProtectedLayout({ children }) {
  return (
    <AuthGate>
      <>
        <DashboardHeader />
        {children}
        <Footer />
        <Scrollup />
      </>
    </AuthGate>
  );
}
