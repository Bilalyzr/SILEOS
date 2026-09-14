import PageHeader from "@/components/public/PageHeader";

const breadcrumbs = [
  { name: "Home", path: "/" },
  { name: "Terms & Conditions", path: "/terms" },
];

export function TermsPage() {
  return (
    <>
      <PageHeader title="Terms and Conditions" breadcrumbs={breadcrumbs} />
      <div className="container-custom py-16">
        <div className="max-w-4xl mx-auto prose prose-lg">
          <div
            className="bg-white rounded-lg shadow-md p-8"
            data-glass="content"
          >
            <h2 className="text-3xl font-bold mb-6 text-neutral-900">
              Terms and Conditions
            </h2>
            <p className="text-neutral-600 mb-6">
              Last updated:{" "}
              {new Date().toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </p>

            <p className="mb-6 text-neutral-700">
              Welcome to SashaInfinity. These Terms and Conditions govern your
              use of our website and services. By accessing or using our
              platform, you agree to be bound by these terms.
            </p>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                1. Acceptance of Terms
              </h3>
              <p className="mb-4 text-neutral-700">
                By registering an account, accessing, or using any part of the
                SashaInfinity platform, you agree to:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>Comply with these Terms and Conditions</li>
                <li>Follow all applicable laws and regulations</li>
                <li>
                  Respect the intellectual property rights of SashaInfinity and
                  our instructors
                </li>
                <li>Use our services only for lawful purposes</li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                2. User Accounts
              </h3>
              <p className="mb-4 text-neutral-700">
                When you create an account with us, you must:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>Provide accurate, complete, and current information</li>
                <li>Maintain the security of your password and account</li>
                <li>Not share your account credentials with others</li>
                <li>
                  Notify us immediately of any unauthorized access to your
                  account
                </li>
                <li>
                  Be responsible for all activities that occur under your
                  account
                </li>
              </ul>
              <p className="mb-4 text-neutral-700">
                We reserve the right to suspend or terminate accounts that
                violate these terms or engage in fraudulent activity.
              </p>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                3. Course Access and Usage
              </h3>
              <p className="mb-4 text-neutral-700">
                When you purchase or enroll in a course:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  You receive a limited, non-exclusive, non-transferable license
                  to access the course content
                </li>
                <li>Course access is for personal, non-commercial use only</li>
                <li>You may not share, distribute, or resell course content</li>
                <li>
                  You may not download course videos for offline viewing unless
                  explicitly permitted
                </li>
                <li>
                  Lifetime access means access as long as the course is hosted
                  on our platform
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                4. Intellectual Property Rights
              </h3>
              <p className="mb-4 text-neutral-700">
                All content on the SashaInfinity platform is protected by
                intellectual property laws:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  Course materials, videos, text, graphics, and logos are owned
                  by SashaInfinity or our instructors
                </li>
                <li>
                  You may not reproduce, distribute, modify, or create
                  derivative works without permission
                </li>
                <li>
                  Unauthorized use of our content may result in legal action
                </li>
                <li>
                  The SashaInfinity name and logo are trademarks and may not be
                  used without authorization
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                5. Instructor Responsibilities
              </h3>
              <p className="mb-4 text-neutral-700">
                If you are an instructor on our platform, you agree to:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>Provide accurate and high-quality course content</li>
                <li>Own or have the rights to all content you upload</li>
                <li>
                  Not upload content that infringes on others' intellectual
                  property
                </li>
                <li>
                  Respond to student questions and provide support in a timely
                  manner
                </li>
                <li>Comply with our course quality standards and guidelines</li>
                <li>
                  Not engage in misleading advertising or false course
                  descriptions
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                6. Payment and Pricing
              </h3>
              <p className="mb-4 text-neutral-700">
                Regarding payments on our platform:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  All prices are listed in Indian Rupees (INR) unless otherwise
                  stated
                </li>
                <li>Prices are subject to change at any time without notice</li>
                <li>
                  Payment must be made in full before accessing paid course
                  content
                </li>
                <li>
                  We accept various payment methods including credit/debit
                  cards, UPI, and net banking
                </li>
                <li>
                  All payments are processed securely through our payment
                  gateway partners
                </li>
                <li>
                  You are responsible for any bank charges or payment gateway
                  fees
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                7. Prohibited Conduct
              </h3>
              <p className="mb-4 text-neutral-700">You are prohibited from:</p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  Using our platform for any illegal or unauthorized purpose
                </li>
                <li>
                  Harassing, threatening, or defaming other users or instructors
                </li>
                <li>Uploading viruses, malware, or any harmful code</li>
                <li>
                  Attempting to gain unauthorized access to our systems or other
                  users' accounts
                </li>
                <li>
                  Scraping, crawling, or using automated tools to access our
                  content
                </li>
                <li>Impersonating another person or entity</li>
                <li>
                  Posting spam, advertising, or promotional content in course
                  discussions
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                8. Disclaimers and Limitations of Liability
              </h3>
              <p className="mb-4 text-neutral-700">
                Please note the following disclaimers:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  Course content is provided "as is" without warranties of any
                  kind
                </li>
                <li>
                  We do not guarantee specific outcomes or results from taking
                  our courses
                </li>
                <li>
                  We are not liable for any indirect, incidental, or
                  consequential damages
                </li>
                <li>
                  Our total liability shall not exceed the amount paid for the
                  course in question
                </li>
                <li>
                  We do not guarantee uninterrupted or error-free access to our
                  platform
                </li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                9. Termination
              </h3>
              <p className="mb-4 text-neutral-700">We reserve the right to:</p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  Suspend or terminate your account for violation of these terms
                </li>
                <li>Remove any content that violates our policies</li>
                <li>
                  Modify or discontinue any part of our services at any time
                </li>
                <li>Refuse service to anyone for any reason</li>
              </ul>
              <p className="mb-4 text-neutral-700">
                Upon termination, your right to access courses and content will
                immediately cease.
              </p>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                10. Modifications to Terms
              </h3>
              <p className="mb-4 text-neutral-700">
                SashaInfinity reserves the right to modify these Terms and
                Conditions at any time. We will notify users of significant
                changes via email or platform notifications. Continued use of
                our services after modifications constitutes acceptance of the
                updated terms.
              </p>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                11. Governing Law
              </h3>
              <p className="mb-4 text-neutral-700">
                These Terms and Conditions are governed by the laws of India.
                Any disputes arising from these terms shall be subject to the
                exclusive jurisdiction of the courts in Salem, Tamil Nadu.
              </p>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                12. Contact Information
              </h3>
              <p className="mb-4 text-neutral-700">
                If you have any questions about these Terms and Conditions,
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
                By using SashaInfinity, you acknowledge that you have read,
                understood, and agree to be bound by these Terms and Conditions.
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
