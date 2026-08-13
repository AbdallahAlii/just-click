import LegalPageShell from "@/components/legal/LegalPageShell";

export const metadata = {
  title: "Privacy | JustClick",
  description: "How JustClick handles account and learning activity data.",
};

export default function PrivacyPage() {
  return (
    <LegalPageShell
      title="Privacy"
      subtitle="A short overview of the information JustClick uses to run the class materials portal."
    >
      <p>
        JustClick is a university class-materials portal. We collect and process
        only what is needed to authenticate users, organize academic access, and
        deliver learning content.
      </p>

      <h2 className="text-lg font-semibold text-ds-text-primary pt-2">
        Information we handle
      </h2>
      <ul className="list-disc pl-5 space-y-1.5">
        <li>Username / student ID and display name</li>
        <li>Email address for verification, approval, and account recovery</li>
        <li>Faculty, department, and semester associations</li>
        <li>
          Material activity such as views, downloads, favorites, and ratings
        </li>
        <li>Comments, questions, and discussion replies on materials</li>
        <li>
          Account verification and security/administration records needed to
          manage access
        </li>
        <li>
          Interactions with JustClick AI related to materials you are allowed to
          access
        </li>
      </ul>

      <h2 className="text-lg font-semibold text-ds-text-primary pt-2">
        Identity and unauthorized registration
      </h2>
      <p>
        You must register and sign in using your own student identity. If
        someone registers with another student&apos;s ID, the relevant
        department or administrator may verify ownership and reject, disable, or
        correct that unauthorized access.
      </p>

      <h2 className="text-lg font-semibold text-ds-text-primary pt-2">
        How we use information
      </h2>
      <p>
        Information is used to provide portal access, send necessary account
        emails, support academic administration, improve material delivery, and
        operate JustClick AI features where enabled.
      </p>

      <h2 className="text-lg font-semibold text-ds-text-primary pt-2">
        Contact
      </h2>
      <p>
        Questions about privacy:{" "}
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
