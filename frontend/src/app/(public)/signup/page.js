import SignupMain from "@/components/layout/main/SignupMain";
import ThemeController from "@/components/shared/others/ThemeController";

export const metadata = {
  title: "Create account | JustClick",
  description: "Create a JustClick student account",
};

const Signup = () => {
  return (
    <main className="bg-ds-page">
      <SignupMain />
      <ThemeController />
    </main>
  );
};

export default Signup;
