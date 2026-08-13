import LegalPageShell from "@/components/legal/LegalPageShell";

export const metadata = {
  title: "Terms | JustClick",
  description: "Terms of use for the JustClick class materials portal.",
};

export default function TermsPage() {
  return (
    <LegalPageShell
      title="Terms of use"
      subtitle="Simple rules for using JustClick responsibly."
    >
      <ul className="list-disc pl-5 space-y-2">
        <li>Provide correct identity information when you register.</li>
        <li>Do not use another student&apos;s ID or pretend to be someone else.</li>
        <li>Do not share your account credentials.</li>
        <li>
          Access materials only according to the permissions granted to your
          account.
        </li>
        <li>
          Do not attempt unauthorized system access, abuse, or interference with
          JustClick services.
        </li>
        <li>
          Comments and questions should stay relevant to the material and remain
          respectful.
        </li>
        <li>
          Abusive, spam, or inappropriate content may be removed by
          administrators.
        </li>
        <li>
          Serious misuse may result in account suspension or other access
          restrictions.
        </li>
        <li>
          Uploaded university and lecturer materials remain the property of
          their respective owners.
        </li>
        <li>
          JustClick AI may make mistakes. Official course materials remain the
          primary academic source.
        </li>
        <li>
          Temporary service interruptions may occur for maintenance or technical
          reasons.
        </li>
      </ul>

      <p className="pt-2">
        Questions:{" "}
        <a
          href="mailto:justclick.cmc@gmail.com"
          className="font-semibold text-ds-action hover:underline"
        >
          justclick.cmc@gmail.com
        </a>
      </p>
    </LegalPageShell>
  );
}
