"use client";

import { useLogin } from "@/features/auth/hooks";
import { getApiErrorMessage } from "@/lib/apiErrors";
import { useSession } from "@/providers/SessionProvider";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";

const LoginForm = () => {
  const router = useRouter();
  const loginMut = useLogin();
  const { user } = useSession();

  const [form, setForm] = useState({
    username: "",
    password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState("");

  useEffect(() => {
    if (user) router.replace("/materials");
  }, [user, router]);

  const onChange = (e) => {
    const { name, value } = e.target;
    setFormError("");
    setForm((p) => ({ ...p, [name]: value }));
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setFormError("");

    if (!form.username.trim() || !form.password.trim()) {
      const msg = "Please enter username and password.";
      setFormError(msg);
      toast.error(msg);
      return;
    }

    try {
      await loginMut.mutateAsync({
        username: form.username.trim(),
        password: form.password,
      });

      toast.success("Login successful.");
      router.replace("/materials");
    } catch (e2) {
      const msg = getApiErrorMessage(e2, "Invalid username or password.");
      setFormError(msg);
      toast.error(msg);
    }
  };

  const labelCls =
    "block text-[12.5px] font-medium text-ds-text-secondary mb-1.5";

  const inputCls =
    "w-full h-11 rounded-lg border border-ds-border " +
    "bg-ds-surface-input px-3.5 text-sm text-ds-text-primary " +
    "placeholder:text-ds-text-muted " +
    "focus:outline-none focus:border-ds-action/50 focus:ring-4 focus:ring-ds-action/10 transition";

  const btnBase =
    "w-full h-11 rounded-lg text-white text-sm font-semibold transition " +
    "focus:outline-none focus:ring-4 focus:ring-ds-action/20";

  const btnEnabled = "bg-ds-action hover:bg-ds-action-hover";
  const btnDisabled = "bg-ds-action/60 cursor-not-allowed";

  const isLoading = loginMut.isPending;

  return (
    <div className="w-full">
      <div className="mb-5">
        <h2 className="text-xl font-semibold text-ds-text-primary">Sign in</h2>
        <p className="mt-1 text-sm text-ds-text-muted">
          New here?{" "}
          <Link
            href="/signup"
            className="font-semibold text-ds-action hover:underline"
          >
            Create account
          </Link>
        </p>
      </div>

      {formError ? (
        <div
          role="alert"
          className="mb-4 rounded-xl border border-ds-error/30 bg-ds-error/10 px-4 py-3 text-sm text-ds-error"
        >
          {formError}
        </div>
      ) : null}

      <form onSubmit={onSubmit} className="space-y-3.5">
        <div>
          <label className={labelCls} htmlFor="username">
            Username <span className="text-ds-error">*</span>
          </label>
          <input
            id="username"
            name="username"
            value={form.username}
            onChange={onChange}
            type="text"
            placeholder="Enter username"
            className={inputCls}
            autoComplete="username"
            disabled={isLoading}
          />
        </div>

        <div>
          <div className="flex items-center justify-between">
            <label className={labelCls} htmlFor="password">
              Password <span className="text-ds-error">*</span>
            </label>

            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="text-xs font-semibold text-ds-action hover:underline disabled:opacity-60"
              disabled={isLoading}
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>

          <input
            id="password"
            name="password"
            value={form.password}
            onChange={onChange}
            type={showPassword ? "text" : "password"}
            placeholder="Enter password"
            className={inputCls}
            autoComplete="current-password"
            disabled={isLoading}
          />
        </div>

        <div className="flex items-center justify-end pt-1">
          <Link
            href="/forgot-password"
            className="text-sm font-semibold text-ds-action hover:underline"
          >
            Forgot password?
          </Link>
        </div>

        <button
          disabled={isLoading}
          type="submit"
          className={`${btnBase} ${isLoading ? btnDisabled : btnEnabled}`}
        >
          {isLoading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
};

export default LoginForm;
