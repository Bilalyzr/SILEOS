import PageHeader from "@/components/public/PageHeader";

const breadcrumbs = [
  { name: "Home", path: "/" },
  { name: "Shipping & Delivery", path: "/shipping" },
];

export function ShippingPage() {
  return (
    <>
      <PageHeader
        title="Shipping and Delivery Policy"
        breadcrumbs={breadcrumbs}
      />
      <div className="container-custom py-16">
        <div className="max-w-4xl mx-auto prose prose-lg">
          <div
            className="bg-white rounded-lg shadow-md p-8"
            data-glass="content"
          >
            <h2 className="text-3xl font-bold mb-6 text-neutral-900">
              Shipping and Delivery Policy
            </h2>
            <p className="text-neutral-600 mb-6">
              Last updated:{" "}
              {new Date().toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </p>

            <div className="mb-8 p-6 bg-primary-50 border-l-4 border-primary-600 rounded">
              <h3 className="text-xl font-semibold mb-3 text-neutral-800">
                Digital Products Only
              </h3>
              <p className="text-neutral-700">
                Sasha Infinity is a <strong>digital learning platform</strong>{" "}
                offering online courses and educational content. All our
                products are delivered digitally via the internet. We do not
                ship physical products unless explicitly stated for special
                merchandise or course materials.
              </p>
            </div>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                1. Instant Digital Delivery
              </h3>
              <p className="mb-4 text-neutral-700">
                Upon successful purchase or enrollment:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  Course access is granted <strong>immediately</strong> after
                  payment confirmation
                </li>
                <li>
                  You will receive a confirmation email with login credentials
                  and course access details
                </li>
                <li>
                  Courses are accessible 24/7 from any device with an internet
                  connection
                </li>
                <li>
                  No physical shipping or delivery charges apply to digital
                  courses
                </li>
                <li>No waiting period - start learning right away!</li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                2. How to Access Your Courses
              </h3>
              <p className="mb-4 text-neutral-700">
                After purchasing a course, follow these steps to access your
                content:
              </p>
              <ol className="list-decimal pl-6 mb-4 text-neutral-700 space-y-3">
                <li>
                  <strong>Login to Your Account:</strong> Use your registered
                  email and password to log in at{" "}
                  <a
                    href="/"
                    className="text-primary-600 hover:text-primary-700"
                  >
                    www.sashainfinity.com
                  </a>
                </li>
                <li>
                  <strong>Navigate to "My Courses":</strong> Click on your
                  profile and select "My Courses" from the dropdown menu
                </li>
                <li>
                  <strong>Select Your Course:</strong> Click on the course you
                  wish to access
                </li>
                <li>
                  <strong>Start Learning:</strong> Browse course content, watch
                  videos, complete assignments, and track your progress
                </li>
              </ol>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                3. Certificate Delivery
              </h3>
              <p className="mb-4 text-neutral-700">
                Upon successful completion of a course:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  Digital certificates are generated automatically upon course
                  completion
                </li>
                <li>
                  Certificates can be downloaded as PDF files from your course
                  dashboard
                </li>
                <li>
                  Certificates include a unique verification ID for authenticity
                </li>
                <li>No additional shipping charges for digital certificates</li>
                <li>
                  If you require a <strong>physical certificate</strong>,
                  additional charges and delivery time will apply (contact
                  support for details)
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                4. Course Materials and Resources
              </h3>
              <p className="mb-4 text-neutral-700">
                All course materials are delivered digitally:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  Video lectures are streamed online (downloadable if permitted
                  by instructor)
                </li>
                <li>
                  PDFs, slides, and documents can be downloaded directly from
                  the course page
                </li>
                <li>
                  Quizzes, assignments, and assessments are completed online
                </li>
                <li>
                  Supplementary resources are provided through downloadable
                  links
                </li>
                <li>All materials are accessible from the course dashboard</li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                5. Physical Products (If Applicable)
              </h3>
              <p className="mb-4 text-neutral-700">
                In rare cases where physical products are offered (such as
                course books, merchandise, or kits):
              </p>

              <h4 className="text-xl font-semibold mb-3 text-neutral-700">
                Shipping Within India
              </h4>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>Standard delivery: 5-7 business days</li>
                <li>Express delivery: 2-3 business days (if available)</li>
                <li>
                  Shipping charges will be calculated at checkout based on
                  location and weight
                </li>
                <li>Free shipping on orders above ₹1000 (if applicable)</li>
              </ul>

              <h4 className="text-xl font-semibold mb-3 text-neutral-700">
                International Shipping
              </h4>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  Delivery time: 10-21 business days depending on destination
                </li>
                <li>
                  International shipping charges will be calculated at checkout
                </li>
                <li>
                  Customs duties and taxes are the responsibility of the
                  recipient
                </li>
              </ul>

              <h4 className="text-xl font-semibold mb-3 text-neutral-700">
                Tracking Information
              </h4>
              <p className="mb-4 text-neutral-700">
                Once your physical order is shipped, you will receive:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>Shipping confirmation email with tracking number</li>
                <li>Courier partner details and estimated delivery date</li>
                <li>Real-time tracking updates via SMS/email</li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                6. Delivery Issues and Support
              </h3>
              <p className="mb-4 text-neutral-700">
                If you experience any issues accessing your course:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>Check your spam/junk folder for the confirmation email</li>
                <li>Ensure you're using the correct login credentials</li>
                <li>Clear your browser cache and cookies</li>
                <li>Try accessing from a different browser or device</li>
                <li>
                  Contact our support team at{" "}
                  <a
                    href="mailto:support@sashainfinity.com"
                    className="text-primary-600 hover:text-primary-700"
                  >
                    support@sashainfinity.com
                  </a>{" "}
                  for assistance
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                7. Refund and Cancellation
              </h3>
              <p className="mb-4 text-neutral-700">
                Since digital courses are delivered instantly:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  Refunds are subject to our Refund Policy (7-day money-back
                  guarantee)
                </li>
                <li>You cannot "return" digital content once accessed</li>
                <li>
                  Refund eligibility depends on course completion percentage
                </li>
                <li>
                  Please review our{" "}
                  <a
                    href="/refund-policy"
                    className="text-primary-600 hover:text-primary-700"
                  >
                    Refund and Returns Policy
                  </a>{" "}
                  for complete details
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                8. Technical Requirements
              </h3>
              <p className="mb-4 text-neutral-700">
                To ensure smooth delivery and access to courses:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>Stable internet connection (minimum 2 Mbps recommended)</li>
                <li>Modern web browser (Chrome, Firefox, Safari, Edge)</li>
                <li>JavaScript and cookies enabled</li>
                <li>
                  Updated operating system (Windows 10+, macOS 10.14+, Android
                  8+, iOS 12+)
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                9. Contact Information
              </h3>
              <p className="mb-4 text-neutral-700">
                For questions about delivery or accessing your courses, please
                contact us:
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
                <p className="mb-2 text-neutral-700">
                  <strong>Support Hours:</strong> Monday - Saturday, 9:00 AM -
                  7:00 PM IST
                </p>
                <p className="text-neutral-700">
                  <strong>Address:</strong> Ward 1, Uthayapuri Colony,
                  Narasothipatti, Salem, Tamil Nadu 636004
                </p>
              </div>
            </section>

            <div className="mt-8 p-4 bg-green-50 border-l-4 border-green-600 rounded">
              <p className="text-sm text-neutral-700">
                <strong>Need Help?</strong> Our support team is available to
                assist you with any delivery or access issues. We typically
                respond within 24 hours during business days.
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
