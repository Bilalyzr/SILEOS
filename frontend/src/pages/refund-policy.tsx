import PageHeader from "@/components/public/PageHeader";

const breadcrumbs = [
  { name: "Home", path: "/" },
  { name: "Refund and Returns", path: "/refund-policy" },
];

export function RefundPolicyPage() {
  return (
    <>
      <PageHeader title="Refund and Returns Policy" breadcrumbs={breadcrumbs} />
      <div className="container-custom py-16">
        <div className="max-w-4xl mx-auto prose prose-lg">
          <div
            className="bg-white rounded-lg shadow-md p-8"
            data-glass="content"
          >
            <h2 className="text-3xl font-bold mb-6 text-neutral-900">
              Refund and Returns Policy
            </h2>
            <p className="text-neutral-600 mb-6">
              Last updated:{" "}
              {new Date().toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </p>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                1. Course Refund Policy
              </h3>
              <p className="mb-4 text-neutral-700">
                At SashaInfinity, we want you to be completely satisfied with
                your course purchase. We offer a
                <strong> 7-day money-back guarantee</strong> for all paid
                courses, subject to the following conditions:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  The refund request must be made within 7 days of the course
                  purchase date
                </li>
                <li>
                  You must have completed less than 30% of the course content
                </li>
                <li>
                  The course must not have been downloaded in its entirety
                </li>
                <li>You must provide a valid reason for the refund request</li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                2. Non-Refundable Items
              </h3>
              <p className="mb-4 text-neutral-700">
                The following items are not eligible for refunds:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  Free courses or courses obtained through promotional offers
                </li>
                <li>Courses purchased more than 7 days ago</li>
                <li>
                  Courses where more than 30% of the content has been completed
                </li>
                <li>Courses that have been fully downloaded</li>
                <li>
                  Subscription fees after the first 7 days of subscription
                </li>
                <li>Certificates and assessment fees</li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                3. How to Request a Refund
              </h3>
              <p className="mb-4 text-neutral-700">
                To request a refund, please follow these steps:
              </p>
              <ol className="list-decimal pl-6 mb-4 text-neutral-700 space-y-2">
                <li>Log in to your SashaInfinity account</li>
                <li>
                  Navigate to "My Courses" and select the course you wish to
                  refund
                </li>
                <li>
                  Click on "Request Refund" and fill out the refund request form
                </li>
                <li>Provide a detailed reason for your refund request</li>
                <li>
                  Submit the form and wait for our team to review your request
                </li>
              </ol>
              <p className="mb-4 text-neutral-700">
                Alternatively, you can contact our support team at{" "}
                <a
                  href="mailto:support@sashainfinity.com"
                  className="text-primary-600 hover:text-primary-700"
                >
                  support@sashainfinity.com
                </a>{" "}
                with your order details and refund request.
              </p>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                4. Refund Processing Time
              </h3>
              <p className="mb-4 text-neutral-700">
                Once your refund request is approved:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>Refunds will be processed within 5-7 business days</li>
                <li>
                  The refund will be credited to your original payment method
                </li>
                <li>
                  Depending on your bank or payment provider, it may take an
                  additional 5-10 business days for the amount to reflect in
                  your account
                </li>
                <li>
                  You will receive an email confirmation once the refund has
                  been processed
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                5. Subscription Cancellations
              </h3>
              <p className="mb-4 text-neutral-700">
                If you have a subscription plan:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  You can cancel your subscription at any time from your account
                  settings
                </li>
                <li>
                  Cancellations will be effective at the end of the current
                  billing period
                </li>
                <li>
                  No refunds will be provided for partial months or unused
                  subscription time
                </li>
                <li>
                  After cancellation, you will retain access to your courses
                  until the end of the billing period
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                6. Technical Issues
              </h3>
              <p className="mb-4 text-neutral-700">
                If you experience technical difficulties accessing your course:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  Please contact our technical support team before requesting a
                  refund
                </li>
                <li>
                  We will work diligently to resolve any technical issues within
                  48 hours
                </li>
                <li>
                  If we are unable to resolve the issue, a full refund will be
                  provided regardless of the 7-day window
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                7. Course Content Updates
              </h3>
              <p className="mb-4 text-neutral-700">
                SashaInfinity reserves the right to:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  Update and modify course content to maintain accuracy and
                  relevance
                </li>
                <li>Remove or discontinue courses at any time</li>
                <li>
                  Students who have purchased a course will retain access to it
                  even if it is discontinued
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                8. Contact Information
              </h3>
              <p className="mb-4 text-neutral-700">
                If you have any questions about our Refund and Returns Policy,
                please contact us:
              </p>
              <div className="bg-neutral-50 p-6 rounded-lg">
                <p className="mb-2 text-neutral-700">
                  <strong>Email:</strong>{" "}
                  <a
                    href="mailto:support@sashainfinity.com"
                    className="text-primary-600 hover:text-primary-700"
                  >
                    support@sashainfinity.com
                  </a>
                </p>
                <p className="mb-2 text-neutral-700">
                  <strong>Phone:</strong> +91 8438740893
                </p>
                <p className="text-neutral-700">
                  <strong>Address:</strong> Ward 1, Uthayapuri Colony,
                  Narasothipatti, Salem, Tamil Nadu 636004
                </p>
              </div>
            </section>

            <div className="mt-8 p-4 bg-primary-50 border-l-4 border-primary-600 rounded">
              <p className="text-sm text-neutral-700">
                This refund and returns policy is subject to change without
                notice. We encourage you to review this page periodically for
                any updates. Your continued use of our services after any
                modifications indicates your acceptance of the updated policy.
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
