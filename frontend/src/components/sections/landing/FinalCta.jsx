import ButtonPrimary from "@/components/shared/buttons/ButtonPrimary";

const FinalCta = () => {
  return (
    <section id="get-started" className="bg-ds-page py-16 sm:py-20 lg:py-24">
      <div className="container">
        <div className="mx-auto max-w-3xl rounded-2xl border border-ds-border bg-ds-surface-secondary px-6 py-10 text-center sm:px-10 sm:py-12">
          <h2 className="text-2xl font-bold tracking-tight text-ds-text-primary sm:text-3xl">
            Ready to study smarter this semester?
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-base text-ds-text-secondary sm:text-lg">
            Stop searching and start learning — everything is organized in one
            place, with AI on every material.
          </p>

          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <ButtonPrimary path="/signup">Create free account</ButtonPrimary>
            <ButtonPrimary variant="secondary" path="/login">
              Log in
            </ButtonPrimary>
          </div>

          <p className="mt-5 text-sm text-ds-text-muted">
            Takes less than 2 minutes.
          </p>
        </div>
      </div>
    </section>
  );
};

export default FinalCta;
