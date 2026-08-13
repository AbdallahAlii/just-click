import LoginMain from "@/components/layout/main/LoginMain";
import ThemeController from "@/components/shared/others/ThemeController";

export const metadata = {
  title: "Login | JustClick",
  description: "Sign in to JustClick",
};

export default function Login() {
  return (
    <main className="bg-ds-page">
      <LoginMain />
      <ThemeController />
    </main>
  );
}
