import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import React, { useState } from "react";
import {
  Save,
  Globe,
  Mail,
  IndianRupee,
  Shield,
  Bell,
  Server,
  Key,
  Lock,
  Eye,
  EyeOff,
} from "lucide-react";
import { api } from "@/api/axios";
import { authAPI } from "@/api/auth";
import toast from "react-hot-toast";

export const AdminSettings: React.FC = () => {
  const [activeTab, setActiveTab] = useState("general");
  const [loading, setLoading] = useState(false);
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false,
  });
  const [passwordData, setPasswordData] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [settings, setSettings] = useState({
    // General Settings
    siteName: "SashaInfinity LMS",
    siteDescription: "Learn and grow with expert-led courses",
    siteUrl: "https://sashainfinity.com",
    adminEmail: "admin@sashainfinity.com",
    timezone: "UTC",
    language: "en",

    // Payment Settings
    currency: "INR",
    currencySymbol: "₹",
    paymentGateway: "razorpay",
    razorpayKey: "",
    razorpaySecret: "",

    // Email Settings
    emailProvider: "smtp",
    smtpHost: "",
    smtpPort: "587",
    smtpUser: "",
    smtpPassword: "",
    emailFrom: "noreply@sashainfinity.com",

    // Course Settings
    autoEnrollFree: true,
    requireApproval: true,
    allowReviews: true,
    allowQA: true,

    // Certificate Settings
    certificateEnabled: true,
    certificateTemplate: "default",

    // Notification Settings
    emailNotifications: true,
    enrollmentNotification: true,
    completionNotification: true,
    newCourseNotification: false,
  });

  const handleSave = async () => {
    setLoading(true);
    try {
      const payload = {
        site_name: settings.siteName,
        site_description: settings.siteDescription,
        site_url: settings.siteUrl,
        admin_email: settings.adminEmail,
        timezone: settings.timezone,
        language: settings.language,
        currency: settings.currency,
        currency_symbol: settings.currencySymbol,
        payment_gateway: settings.paymentGateway,
        razorpay_key: settings.razorpayKey,
        razorpay_secret: settings.razorpaySecret,
        email_provider: settings.emailProvider,
        smtp_host: settings.smtpHost,
        smtp_port: settings.smtpPort,
        smtp_user: settings.smtpUser,
        smtp_password: settings.smtpPassword,
        email_from: settings.emailFrom,
        auto_enroll_free: settings.autoEnrollFree,
        require_approval: settings.requireApproval,
        allow_reviews: settings.allowReviews,
        allow_qa: settings.allowQA,
        certificate_enabled: settings.certificateEnabled,
        certificate_template: settings.certificateTemplate,
        email_notifications: settings.emailNotifications,
        enrollment_notification: settings.enrollmentNotification,
        completion_notification: settings.completionNotification,
        new_course_notification: settings.newCourseNotification,
      };

      await api.put("/admin/settings", payload);
      toast.success("Settings saved successfully");
    } catch (error: any) {
      console.error("Error saving settings:", error);
      toast.error(error.response?.data?.detail || "Failed to save settings");
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      toast.error("New passwords do not match");
      return;
    }
    if (passwordData.newPassword.length < 8) {
      toast.error("Password must be at least 8 characters");
      return;
    }
    if (!/[A-Z]/.test(passwordData.newPassword)) {
      toast.error("Password must contain at least one uppercase letter");
      return;
    }
    if (!/[a-z]/.test(passwordData.newPassword)) {
      toast.error("Password must contain at least one lowercase letter");
      return;
    }
    if (!/[0-9]/.test(passwordData.newPassword)) {
      toast.error("Password must contain at least one number");
      return;
    }
    setPasswordLoading(true);
    try {
      await authAPI.changePassword({
        currentPassword: passwordData.currentPassword,
        newPassword: passwordData.newPassword,
      });
      toast.success("Password changed successfully");
      setPasswordData({
        currentPassword: "",
        newPassword: "",
        confirmPassword: "",
      });
    } catch (error: any) {
      console.error("Password change error:", error);
      toast.error(error.response?.data?.detail || "Failed to change password");
    } finally {
      setPasswordLoading(false);
    }
  };

  const togglePasswordVisibility = (field: "current" | "new" | "confirm") => {
    setShowPasswords((prev) => ({ ...prev, [field]: !prev[field] }));
  };

  const tabs = [
    { id: "general", name: "General", icon: Globe },
    { id: "payment", name: "Payment", icon: IndianRupee },
    { id: "email", name: "Email", icon: Mail },
    { id: "courses", name: "Courses", icon: Server },
    { id: "certificates", name: "Certificates", icon: Shield },
    { id: "notifications", name: "Notifications", icon: Bell },
    { id: "security", name: "Security", icon: Lock },
  ];

  return (
    <PageLayout
      header={
        <PageHeader>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
            <p className="text-gray-600 mt-1">
              Configure your LMS platform settings
            </p>
          </div>
          <button
            onClick={handleSave}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save className="w-4 h-4" />
            <span>{loading ? "Saving..." : "Save Changes"}</span>
          </button>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-settings"
    >
      <div className="flex gap-6">
        {/* Sidebar Tabs */}
        <div
          className="w-64 bg-white rounded-lg border border-gray-200 p-4 h-fit"
          data-glass="content"
        >
          <nav className="space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === tab.id
                      ? "bg-blue-50 text-blue-600"
                      : "text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span>{tab.name}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Settings Content */}
        <div
          className="flex-1 bg-white rounded-lg border border-gray-200 p-6"
          data-glass="work"
        >
          {/* General Settings */}
          {activeTab === "general" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  General Settings
                </h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Site Name
                    </label>
                    <input
                      type="text"
                      value={settings.siteName}
                      onChange={(e) =>
                        setSettings({ ...settings, siteName: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Site Description
                    </label>
                    <textarea
                      value={settings.siteDescription}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          siteDescription: e.target.value,
                        })
                      }
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Site URL
                    </label>
                    <input
                      type="url"
                      value={settings.siteUrl}
                      onChange={(e) =>
                        setSettings({ ...settings, siteUrl: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Admin Email
                    </label>
                    <input
                      type="email"
                      value={settings.adminEmail}
                      onChange={(e) =>
                        setSettings({ ...settings, adminEmail: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Timezone
                      </label>
                      <select
                        value={settings.timezone}
                        onChange={(e) =>
                          setSettings({ ...settings, timezone: e.target.value })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="UTC">UTC</option>
                        <option value="Asia/Kolkata">Asia/Kolkata</option>
                        <option value="America/New_York">
                          America/New_York
                        </option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Language
                      </label>
                      <select
                        value={settings.language}
                        onChange={(e) =>
                          setSettings({ ...settings, language: e.target.value })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="en">English</option>
                        <option value="hi">Hindi</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Payment Settings */}
          {activeTab === "payment" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  Payment Settings
                </h2>
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Currency
                      </label>
                      <select
                        value={settings.currency}
                        onChange={(e) =>
                          setSettings({ ...settings, currency: e.target.value })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="INR">INR - Indian Rupee</option>
                        <option value="USD">USD - US Dollar</option>
                        <option value="EUR">EUR - Euro</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Currency Symbol
                      </label>
                      <input
                        type="text"
                        value={settings.currencySymbol}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            currencySymbol: e.target.value,
                          })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Payment Gateway
                    </label>
                    <select
                      value={settings.paymentGateway}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          paymentGateway: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="razorpay">Razorpay</option>
                      <option value="stripe">Stripe</option>
                      <option value="paypal">PayPal</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Razorpay Key
                    </label>
                    <input
                      type="text"
                      value={settings.razorpayKey}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          razorpayKey: e.target.value,
                        })
                      }
                      placeholder="rzp_test_xxxxxxxxxxxxx"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Razorpay Secret
                    </label>
                    <input
                      type="password"
                      value={settings.razorpaySecret}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          razorpaySecret: e.target.value,
                        })
                      }
                      placeholder="••••••••••••••••"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Email Settings */}
          {activeTab === "email" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  Email Settings
                </h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Email Provider
                    </label>
                    <select
                      value={settings.emailProvider}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          emailProvider: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="smtp">SMTP</option>
                      <option value="sendgrid">SendGrid</option>
                      <option value="mailgun">Mailgun</option>
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        SMTP Host
                      </label>
                      <input
                        type="text"
                        value={settings.smtpHost}
                        onChange={(e) =>
                          setSettings({ ...settings, smtpHost: e.target.value })
                        }
                        placeholder="smtp.gmail.com"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        SMTP Port
                      </label>
                      <input
                        type="text"
                        value={settings.smtpPort}
                        onChange={(e) =>
                          setSettings({ ...settings, smtpPort: e.target.value })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      SMTP Username
                    </label>
                    <input
                      type="text"
                      value={settings.smtpUser}
                      onChange={(e) =>
                        setSettings({ ...settings, smtpUser: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      SMTP Password
                    </label>
                    <input
                      type="password"
                      value={settings.smtpPassword}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          smtpPassword: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      From Email
                    </label>
                    <input
                      type="email"
                      value={settings.emailFrom}
                      onChange={(e) =>
                        setSettings({ ...settings, emailFrom: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Course Settings */}
          {activeTab === "courses" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  Course Settings
                </h2>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-900">
                        Auto-enroll for Free Courses
                      </p>
                      <p className="text-sm text-gray-600">
                        Automatically enroll students in free courses
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.autoEnrollFree}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            autoEnrollFree: e.target.checked,
                          })
                        }
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-900">
                        Require Admin Approval
                      </p>
                      <p className="text-sm text-gray-600">
                        Courses need admin approval before publishing
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.requireApproval}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            requireApproval: e.target.checked,
                          })
                        }
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-900">
                        Allow Course Reviews
                      </p>
                      <p className="text-sm text-gray-600">
                        Enable students to review courses
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.allowReviews}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            allowReviews: e.target.checked,
                          })
                        }
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-900">Allow Q&A</p>
                      <p className="text-sm text-gray-600">
                        Enable Q&A section in courses
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.allowQA}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            allowQA: e.target.checked,
                          })
                        }
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Certificate Settings */}
          {activeTab === "certificates" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  Certificate Settings
                </h2>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-900">
                        Enable Certificates
                      </p>
                      <p className="text-sm text-gray-600">
                        Issue certificates upon course completion
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.certificateEnabled}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            certificateEnabled: e.target.checked,
                          })
                        }
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Certificate Template
                    </label>
                    <select
                      value={settings.certificateTemplate}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          certificateTemplate: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="default">Default Template</option>
                      <option value="modern">Modern Template</option>
                      <option value="classic">Classic Template</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Notification Settings */}
          {activeTab === "notifications" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  Notification Settings
                </h2>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-900">
                        Email Notifications
                      </p>
                      <p className="text-sm text-gray-600">
                        Send email notifications to users
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.emailNotifications}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            emailNotifications: e.target.checked,
                          })
                        }
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-900">
                        Enrollment Notifications
                      </p>
                      <p className="text-sm text-gray-600">
                        Notify on new course enrollments
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.enrollmentNotification}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            enrollmentNotification: e.target.checked,
                          })
                        }
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-900">
                        Completion Notifications
                      </p>
                      <p className="text-sm text-gray-600">
                        Notify on course completion
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.completionNotification}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            completionNotification: e.target.checked,
                          })
                        }
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-900">
                        New Course Notifications
                      </p>
                      <p className="text-sm text-gray-600">
                        Notify students about new courses
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.newCourseNotification}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            newCourseNotification: e.target.checked,
                          })
                        }
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Security Settings */}
          {activeTab === "security" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  Change Password
                </h2>
                <form
                  onSubmit={handlePasswordChange}
                  className="space-y-4 max-w-md"
                >
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Current Password
                    </label>
                    <div className="relative">
                      <input
                        type={showPasswords.current ? "text" : "password"}
                        value={passwordData.currentPassword}
                        onChange={(e) =>
                          setPasswordData({
                            ...passwordData,
                            currentPassword: e.target.value,
                          })
                        }
                        required
                        className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                      <button
                        type="button"
                        onClick={() => togglePasswordVisibility("current")}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                      >
                        {showPasswords.current ? (
                          <EyeOff className="w-5 h-5" />
                        ) : (
                          <Eye className="w-5 h-5" />
                        )}
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      New Password
                    </label>
                    <div className="relative">
                      <input
                        type={showPasswords.new ? "text" : "password"}
                        value={passwordData.newPassword}
                        onChange={(e) =>
                          setPasswordData({
                            ...passwordData,
                            newPassword: e.target.value,
                          })
                        }
                        required
                        minLength={8}
                        className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                      <button
                        type="button"
                        onClick={() => togglePasswordVisibility("new")}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                      >
                        {showPasswords.new ? (
                          <EyeOff className="w-5 h-5" />
                        ) : (
                          <Eye className="w-5 h-5" />
                        )}
                      </button>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      Min 8 chars, uppercase, lowercase, number
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Confirm New Password
                    </label>
                    <div className="relative">
                      <input
                        type={showPasswords.confirm ? "text" : "password"}
                        value={passwordData.confirmPassword}
                        onChange={(e) =>
                          setPasswordData({
                            ...passwordData,
                            confirmPassword: e.target.value,
                          })
                        }
                        required
                        minLength={8}
                        className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                      <button
                        type="button"
                        onClick={() => togglePasswordVisibility("confirm")}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                      >
                        {showPasswords.confirm ? (
                          <EyeOff className="w-5 h-5" />
                        ) : (
                          <Eye className="w-5 h-5" />
                        )}
                      </button>
                    </div>
                  </div>
                  <div className="pt-2">
                    <button
                      type="submit"
                      disabled={passwordLoading}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Key className="w-4 h-4" />
                      <span>
                        {passwordLoading ? "Changing..." : "Change Password"}
                      </span>
                    </button>
                  </div>
                </form>
              </div>

              <div className="border-t border-gray-200 pt-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">
                  Password Requirements
                </h3>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-green-500" />
                    Minimum 8 characters
                  </li>
                  <li className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-green-500" />
                    At least one uppercase letter (A-Z)
                  </li>
                  <li className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-green-500" />
                    At least one lowercase letter (a-z)
                  </li>
                  <li className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-green-500" />
                    At least one number (0-9)
                  </li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
};
