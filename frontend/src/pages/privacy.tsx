import PageHeader from "@/components/public/PageHeader";

const breadcrumbs = [
  { name: "Home", path: "/" },
  { name: "Privacy Policy", path: "/privacy" },
];

export function PrivacyPage() {
  return (
    <>
      <PageHeader title="Privacy Policy" breadcrumbs={breadcrumbs} />
      <div className="container-custom py-16">
        <div className="max-w-4xl mx-auto prose prose-lg">
          <div className="bg-white rounded-lg shadow-md p-8" data-glass="work">
            <h2 className="text-3xl font-bold mb-6 text-neutral-900">
              Privacy Policy
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
              At SashaInfinity, we are committed to protecting your privacy and
              ensuring the security of your personal information. This Privacy
              Policy explains how we collect, use, disclose, and safeguard your
              information when you use our platform.
            </p>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                1. Information We Collect
              </h3>

              <h4 className="text-xl font-semibold mb-3 text-neutral-700">
                Personal Information
              </h4>
              <p className="mb-4 text-neutral-700">
                We collect information that you provide directly to us,
                including:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>Name, email address, and contact information</li>
                <li>Username and password</li>
                <li>Profile photo and bio</li>
                <li>Payment and billing information</li>
                <li>Educational background and preferences</li>
                <li>Course enrollment and progress data</li>
              </ul>

              <h4 className="text-xl font-semibold mb-3 text-neutral-700">
                Automatically Collected Information
              </h4>
              <p className="mb-4 text-neutral-700">
                When you use our platform, we automatically collect:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  Device information (IP address, browser type, operating
                  system)
                </li>
                <li>Usage data (pages viewed, time spent, courses accessed)</li>
                <li>Cookies and similar tracking technologies</li>
                <li>
                  Location data (approximate location based on IP address)
                </li>
              </ul>

              <h4 className="text-xl font-semibold mb-3 text-neutral-700">
                Device Permissions Used by Our Mobile App
              </h4>
              <p className="mb-4 text-neutral-700">
                The SashaInfinity Android app (com.sashainfinity.sasha_lms)
                requests the following device permissions. Each is requested
                only when you first use the feature that needs it, and you can
                decline or revoke it in your device settings at any time.
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  <strong>Camera</strong> — used only if you choose to take a
                  new profile photo. Our 3D and AR model gallery does{" "}
                  <em>not</em> use the in-app camera: when you tap "View in your
                  space", the model is handed to Google's Scene Viewer app,
                  which manages that AR session and its own camera access.
                </li>
                <li>
                  <strong>Photos and media</strong> — used only when you pick an
                  existing image from your gallery as a profile photo. We access
                  the single image you select and do not scan your photo
                  library.
                </li>
                <li>
                  <strong>Notifications</strong> — used to deliver course
                  updates and announcements you have opted into.
                </li>
              </ul>

              <h4 className="text-xl font-semibold mb-3 text-neutral-700">
                Information Collected by Our Mobile App
              </h4>
              <p className="mb-4 text-neutral-700">
                The app collects the following in addition to the above. Each is
                used only for the feature described and is never sold.
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  <strong>Camera and photos:</strong> accessed only when you
                  choose to set a profile picture, either by taking a photo or
                  picking one from your gallery. The selected image is uploaded
                  to your profile; we do not scan or access any other media on
                  your device.
                </li>
                <li>
                  <strong>Device identifiers (push token):</strong> a Firebase
                  Cloud Messaging token so we can deliver course updates and
                  announcements you have opted into. You can disable
                  notifications at any time in your device settings.
                </li>
                <li>
                  <strong>Advertising ID:</strong> present via Google Analytics
                  for Firebase. We use it for aggregate product analytics only.
                  We do <strong>not</strong> show ads, build advertising
                  profiles, or share it with advertising networks.
                </li>
                <li>
                  <strong>Crash and diagnostic data:</strong> collected through
                  Firebase Crashlytics to diagnose and fix app crashes.
                </li>
                <li>
                  <strong>Purchase information:</strong> when you buy a course,
                  payment is processed by Razorpay. We receive confirmation of
                  the transaction and your enrolment; your full card details are
                  handled by Razorpay and never stored on our servers.
                </li>
              </ul>
              <p className="mb-4 text-neutral-700">
                All data sent between the app and our servers is encrypted in
                transit over HTTPS. You can request deletion of your account and
                associated data at any time &mdash; see{" "}
                <a
                  href="#account-deletion"
                  className="text-primary-600 hover:text-primary-700"
                >
                  How to delete your account and data
                </a>
                .
              </p>

              <h4 className="text-xl font-semibold mb-3 text-neutral-700">
                Summary by data category
              </h4>
              <p className="mb-4 text-neutral-700">
                The table below maps what we collect to the categories used in
                the Google Play Data safety section.
              </p>
              <div className="overflow-x-auto mb-4">
                <table className="min-w-full text-left text-neutral-700">
                  <thead>
                    <tr className="border-b border-neutral-300">
                      <th className="py-2 pr-4 font-semibold">Category</th>
                      <th className="py-2 pr-4 font-semibold">
                        What we collect
                      </th>
                      <th className="py-2 pr-4 font-semibold">Why</th>
                      <th className="py-2 font-semibold">Shared with</th>
                    </tr>
                  </thead>
                  <tbody className="align-top">
                    <tr className="border-b border-neutral-200">
                      <td className="py-2 pr-4">Personal info</td>
                      <td className="py-2 pr-4">
                        Name, email, phone, profile photo, bio
                      </td>
                      <td className="py-2 pr-4">
                        Account creation, support, certificates
                      </td>
                      <td className="py-2">
                        Course instructors; Google Sign-In if used
                      </td>
                    </tr>
                    <tr className="border-b border-neutral-200">
                      <td className="py-2 pr-4">Financial info</td>
                      <td className="py-2 pr-4">
                        Purchase history and order details
                      </td>
                      <td className="py-2 pr-4">Processing course purchases</td>
                      <td className="py-2">Razorpay</td>
                    </tr>
                    <tr className="border-b border-neutral-200">
                      <td className="py-2 pr-4">Photos</td>
                      <td className="py-2 pr-4">
                        A profile picture you choose to upload
                      </td>
                      <td className="py-2 pr-4">Displaying your profile</td>
                      <td className="py-2">Not shared</td>
                    </tr>
                    <tr className="border-b border-neutral-200">
                      <td className="py-2 pr-4">App activity</td>
                      <td className="py-2 pr-4">
                        Courses accessed, lesson progress, quiz results, in-app
                        events
                      </td>
                      <td className="py-2 pr-4">
                        Delivering the course, tracking progress, analytics
                      </td>
                      <td className="py-2">
                        Google Analytics for Firebase (aggregate)
                      </td>
                    </tr>
                    <tr className="border-b border-neutral-200">
                      <td className="py-2 pr-4">Device or other IDs</td>
                      <td className="py-2 pr-4">
                        Push token, advertising ID, device and OS details
                      </td>
                      <td className="py-2 pr-4">
                        Notifications, analytics, crash diagnostics
                      </td>
                      <td className="py-2">
                        Firebase Cloud Messaging, Analytics, Crashlytics
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2 pr-4">App info and performance</td>
                      <td className="py-2 pr-4">Crash logs and diagnostics</td>
                      <td className="py-2 pr-4">
                        Fixing bugs and stability issues
                      </td>
                      <td className="py-2">Firebase Crashlytics</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                2. How We Use Your Information
              </h3>
              <p className="mb-4 text-neutral-700">
                We use the information we collect to:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>Provide, maintain, and improve our services</li>
                <li>Process your course enrollments and payments</li>
                <li>
                  Send you course updates, certificates, and important
                  notifications
                </li>
                <li>
                  Personalize your learning experience and recommend relevant
                  courses
                </li>
                <li>
                  Respond to your comments, questions, and support requests
                </li>
                <li>Monitor and analyze usage patterns and trends</li>
                <li>
                  Detect, prevent, and address technical issues and fraudulent
                  activity
                </li>
                <li>Send marketing communications (with your consent)</li>
                <li>Comply with legal obligations</li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                3. Information Sharing and Disclosure
              </h3>
              <p className="mb-4 text-neutral-700">
                We may share your information in the following circumstances:
              </p>

              <h4 className="text-xl font-semibold mb-3 text-neutral-700">
                With Instructors
              </h4>
              <p className="mb-4 text-neutral-700">
                When you enroll in a course, we share your name and email with
                the instructor to facilitate communication and support.
              </p>

              <h4 className="text-xl font-semibold mb-3 text-neutral-700">
                With Service Providers
              </h4>
              <p className="mb-4 text-neutral-700">
                We rely on the following named third parties. Each receives only
                the data listed, and only to perform that function for us:
              </p>
              <div className="overflow-x-auto mb-4">
                <table className="min-w-full text-left text-neutral-700">
                  <thead>
                    <tr className="border-b border-neutral-300">
                      <th className="py-2 pr-4 font-semibold">Service</th>
                      <th className="py-2 pr-4 font-semibold">Purpose</th>
                      <th className="py-2 font-semibold">Data shared</th>
                    </tr>
                  </thead>
                  <tbody className="align-top">
                    <tr className="border-b border-neutral-200">
                      <td className="py-2 pr-4">Razorpay</td>
                      <td className="py-2 pr-4">
                        Payment processing for course purchases
                      </td>
                      <td className="py-2">
                        Name, email, phone, order and payment details. Card
                        details are entered in Razorpay&apos;s own checkout and
                        are never stored by us.
                      </td>
                    </tr>
                    <tr className="border-b border-neutral-200">
                      <td className="py-2 pr-4">
                        Google Sign-In (Firebase Authentication)
                      </td>
                      <td className="py-2 pr-4">
                        Optional sign-in and account verification
                      </td>
                      <td className="py-2">
                        Your Google account email, name and profile photo.
                      </td>
                    </tr>
                    <tr className="border-b border-neutral-200">
                      <td className="py-2 pr-4">Firebase Cloud Messaging</td>
                      <td className="py-2 pr-4">
                        Push notifications for course updates
                      </td>
                      <td className="py-2">A device push token.</td>
                    </tr>
                    <tr className="border-b border-neutral-200">
                      <td className="py-2 pr-4">
                        Google Analytics for Firebase &amp; Crashlytics
                      </td>
                      <td className="py-2 pr-4">
                        Aggregate product analytics and crash diagnostics
                      </td>
                      <td className="py-2">
                        App interaction events, device model and OS, advertising
                        ID, crash reports. Not used for advertising.
                      </td>
                    </tr>
                    <tr className="border-b border-neutral-200">
                      <td className="py-2 pr-4">YouTube and Bunny.net CDN</td>
                      <td className="py-2 pr-4">
                        Hosting and streaming course video
                      </td>
                      <td className="py-2">
                        Playback requests, including IP address and
                        device/player information, as required to deliver the
                        video.
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2 pr-4">Google Scene Viewer</td>
                      <td className="py-2 pr-4">
                        Displays a 3D model in your real-world space when you
                        choose AR view
                      </td>
                      <td className="py-2">
                        The model file being viewed. The AR camera session is
                        handled entirely by Google&apos;s app, not by us.
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="mb-4 text-neutral-700">
                We also use service providers for email delivery, cloud hosting
                and storage, and customer support. We do not sell your personal
                information.
              </p>

              <h4 className="text-xl font-semibold mb-3 text-neutral-700">
                For Legal Reasons
              </h4>
              <p className="mb-4 text-neutral-700">
                We may disclose your information if required by law or in
                response to:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>Legal processes (court orders, subpoenas)</li>
                <li>Government or law enforcement requests</li>
                <li>Protection of our rights, property, or safety</li>
                <li>Investigation of fraud or security issues</li>
              </ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                4. Data Security
              </h3>
              <p className="mb-4 text-neutral-700">
                We implement appropriate security measures to protect your
                personal information:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>Encryption of data in transit and at rest</li>
                <li>
                  Secure server infrastructure with regular security audits
                </li>
                <li>Access controls and authentication mechanisms</li>
                <li>Regular backups and disaster recovery procedures</li>
                <li>Employee training on data protection practices</li>
              </ul>
              <p className="mb-4 text-neutral-700">
                However, no method of transmission over the internet is 100%
                secure. While we strive to protect your information, we cannot
                guarantee absolute security.
              </p>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                5. Cookies and Tracking Technologies
              </h3>
              <p className="mb-4 text-neutral-700">
                We use cookies and similar technologies to:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>Remember your preferences and settings</li>
                <li>Keep you logged in to your account</li>
                <li>Analyze how you use our platform</li>
                <li>Deliver personalized course recommendations</li>
                <li>Measure the effectiveness of our marketing campaigns</li>
              </ul>
              <p className="mb-4 text-neutral-700">
                You can control cookies through your browser settings. However,
                disabling cookies may affect your ability to use certain
                features of our platform.
              </p>
              <p className="mb-4 text-neutral-700">
                We do not display third-party advertising, and we do not use
                your data to build advertising profiles or share it with
                advertising networks.
              </p>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                6. Your Data Rights
              </h3>
              <p className="mb-4 text-neutral-700">
                You have the following rights regarding your personal
                information:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>
                  <strong>Access:</strong> Request a copy of the personal data
                  we hold about you
                </li>
                <li>
                  <strong>Correction:</strong> Update or correct inaccurate
                  information in your account settings
                </li>
                <li>
                  <strong>Deletion:</strong> Request deletion of your account
                  and associated data
                </li>
                <li>
                  <strong>Portability:</strong> Request a copy of your data in a
                  machine-readable format
                </li>
                <li>
                  <strong>Opt-out:</strong> Unsubscribe from marketing
                  communications at any time
                </li>
                <li>
                  <strong>Restriction:</strong> Request restriction of
                  processing in certain circumstances
                </li>
              </ul>
              <p className="mb-4 text-neutral-700">
                To exercise any of these rights, please contact us at{" "}
                <a
                  href="mailto:privacy@sashainfinity.com"
                  className="text-primary-600 hover:text-primary-700"
                >
                  privacy@sashainfinity.com
                </a>
              </p>

              <h4
                className="text-xl font-semibold mb-3 text-neutral-700"
                id="account-deletion"
              >
                How to delete your account and data
              </h4>
              <p className="mb-4 text-neutral-700">
                To request deletion of your SashaInfinity account and the
                personal data associated with it, email{" "}
                <a
                  href="mailto:privacy@sashainfinity.com?subject=Account%20deletion%20request"
                  className="text-primary-600 hover:text-primary-700"
                >
                  privacy@sashainfinity.com
                </a>{" "}
                from the email address registered to your account, with the
                subject &quot;Account deletion request&quot;. You can also write
                to us at the postal address in the Contact section below.
              </p>
              <p className="mb-4 text-neutral-700">
                We will verify the request and action it within 30 days.
                Deleting your account removes your profile, profile photo,
                course enrolments and progress data. We retain a minimal record
                of completed transactions where tax and accounting law requires
                it, and any certificate you have already been issued remains
                verifiable unless you ask us to revoke it.
              </p>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                7. Data Retention
              </h3>
              <p className="mb-4 text-neutral-700">
                We retain your personal information for as long as necessary to:
              </p>
              <ul className="list-disc pl-6 mb-4 text-neutral-700 space-y-2">
                <li>Provide our services and maintain your account</li>
                <li>Comply with legal obligations and resolve disputes</li>
                <li>Enforce our agreements and protect our rights</li>
              </ul>
              <p className="mb-4 text-neutral-700">
                When you delete your account, we will delete or anonymize your
                personal information, except where we are required to retain it
                for legal or legitimate business purposes.
              </p>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                8. Children's Privacy
              </h3>
              <p className="mb-4 text-neutral-700">
                SashaInfinity is intended for learners aged 13 and over. Our
                courses are used by teenage students (13&ndash;17) as well as
                adults, including through partnerships with schools and
                colleges.
              </p>
              <p className="mb-4 text-neutral-700">
                We do not knowingly collect personal information from children
                under 13. If you are a parent or guardian and believe a child
                under 13 has created an account or provided us with personal
                information, please contact us at{" "}
                <a
                  href="mailto:privacy@sashainfinity.com"
                  className="text-primary-600 hover:text-primary-700"
                >
                  privacy@sashainfinity.com
                </a>{" "}
                and we will delete that information.
              </p>
              <p className="mb-4 text-neutral-700">
                If you are between 13 and 17, please review this policy with a
                parent or guardian before creating an account. Where a school or
                institution enrols students on our platform, that institution is
                responsible for obtaining any parental consent required in its
                jurisdiction.
              </p>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                9. International Data Transfers
              </h3>
              <p className="mb-4 text-neutral-700">
                Your information may be transferred to and processed in
                countries other than India. We ensure that appropriate
                safeguards are in place to protect your data in accordance with
                this Privacy Policy.
              </p>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                10. Changes to This Privacy Policy
              </h3>
              <p className="mb-4 text-neutral-700">
                We may update this Privacy Policy from time to time. We will
                notify you of significant changes via email or through a notice
                on our platform. We encourage you to review this policy
                periodically.
              </p>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-4 text-neutral-800">
                11. Contact Us
              </h3>
              <p className="mb-4 text-neutral-700">
                If you have any questions or concerns about this Privacy Policy
                or our data practices, please contact us:
              </p>
              <div className="bg-neutral-50 p-6 rounded-lg">
                <p className="mb-2 text-neutral-700">
                  <strong>Email:</strong>{" "}
                  <a
                    href="mailto:privacy@sashainfinity.com"
                    className="text-primary-600 hover:text-primary-700"
                  >
                    privacy@sashainfinity.com
                  </a>
                </p>
                <p className="mb-2 text-neutral-700">
                  <strong>Support:</strong>{" "}
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
                By using SashaInfinity, you acknowledge that you have read and
                understood this Privacy Policy and consent to the collection,
                use, and disclosure of your information as described herein.
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
