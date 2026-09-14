import { AstraSymbol } from "@/components/design-system/AstraSymbol";
import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useCallback } from "react";
import React, { useState, useEffect } from "react";
import { track } from "@/api/funnel";
import { Lock, Check, ArrowLeft, Loader2, X } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useCart } from "@/contexts/CartContext";
import { useAuthStore } from "@/store/auth";
import toast from "react-hot-toast";
import { courseAPI } from "@/api/course";
import { api } from "@/api/axios";
import { validateCoupon, type CouponValidationResponse } from "@/api/cart";

export function CheckoutPage() {
  const navigate = useNavigate();
  const { courseId } = useParams<{ courseId?: string }>();
  const {
    items,
    appliedCoupon,
    getFinalTotal,
    checkout: cartCheckout,
    clearCart,
  } = useCart();
  const user = useAuthStore((s) => s.user);
  const [couponCode, setCouponCode] = useState("");
  const [processing, setProcessing] = useState(false);
  const [orderComplete, setOrderComplete] = useState(false);
  const [, setOrderId] = useState<number | null>(null);
  const [directCourse, setDirectCourse] = useState<any>(null);
  const [loadingCourse, setLoadingCourse] = useState(false);
  const [isDirectCheckout, setIsDirectCheckout] = useState(false);
  // Whether the success screen was reached by redeeming a voucher/free-enroll
  // rather than by completing a Razorpay payment. Drives copy on the success card.
  const [redeemedViaCode, setRedeemedViaCode] = useState(false);
  // Success-page countdown — MUST live at component top level. Hooks
  // inside `if (orderComplete)` violate Rules of Hooks and crash React
  // with error #310 when the flag flips.
  const [countdown, setCountdown] = useState(5);
  // Validated coupon for direct checkout
  const [validatedCoupon, setValidatedCoupon] =
    useState<CouponValidationResponse | null>(null);
  const [validatingCoupon, setValidatingCoupon] = useState(false);

  // Check if this is direct checkout (single course)
  const fetchCourseInfo = useCallback(async () => {
    if (!courseId) return;
    try {
      setLoadingCourse(true);
      const info = await courseAPI.getCheckoutInfo(parseInt(courseId));
      setDirectCourse(info);
    } catch (error) {
      console.error("Error fetching course info:", error);
      toast.error("Failed to load course information");
      navigate("/courses");
    } finally {
      setLoadingCourse(false);
    }
  }, [courseId, navigate]);
  useEffect(() => {
    if (courseId) {
      setIsDirectCheckout(true);
      fetchCourseInfo();
    }
  }, [courseId, fetchCourseInfo]);

  // Redirect if cart is empty and this is NOT a direct-checkout URL.
  // Gate on courseId (synchronous from useParams) rather than the derived
  // isDirectCheckout flag — otherwise this effect fires on the first render
  // before the flag flip commits, sending every /checkout/:courseId visitor
  // to an empty cart.
  useEffect(() => {
    if (!courseId && items.length === 0 && !orderComplete) {
      navigate("/cart");
    }
  }, [items, orderComplete, navigate, courseId]);

  const subtotal = items.reduce((sum, item) => {
    const price = item.salePrice ?? item.price;
    return sum + price;
  }, 0);

  const couponDiscount = appliedCoupon ? appliedCoupon.discountAmount : 0;
  const tax = 0; // No tax for now

  // Calculate total for direct checkout with validated coupon
  const basePrice =
    isDirectCheckout && directCourse
      ? directCourse.sale_price || directCourse.price
      : subtotal;

  const directCouponDiscount = validatedCoupon?.discount_amount || 0;
  // Cart mode must use the cart context's coupon-aware total — the raw
  // subtotal here ignored the applied cart coupon, overcharging by the
  // discount amount. The CTA below renders this total.
  const total = isDirectCheckout
    ? basePrice - directCouponDiscount
    : getFinalTotal();

  // A voucher is an INTR-XXXX-style code. We don't need to be strict —
  // the backend resolver makes the final call. This only informs button copy.
  const trimmedCode = couponCode.trim();
  const looksLikeVoucher = /^INTR-/i.test(trimmedCode);

  // Validate coupon for direct checkout
  const handleValidateCoupon = async () => {
    if (!trimmedCode || !directCourse) return;

    setValidatingCoupon(true);
    try {
      const result = await validateCoupon(
        trimmedCode,
        [directCourse.course_id],
        basePrice,
      );
      if (result.valid) {
        setValidatedCoupon(result);
        toast.success(`Coupon applied: ${result.message}`);
      } else {
        setValidatedCoupon(null);
        toast.error(result.message);
      }
    } catch (error: any) {
      console.error("Coupon validation error:", error);
      setValidatedCoupon(null);
      toast.error(error?.response?.data?.detail || "Failed to validate coupon");
    } finally {
      setValidatingCoupon(false);
    }
  };

  const handleRemoveCoupon = () => {
    setCouponCode("");
    setValidatedCoupon(null);
  };

  const ensureRazorpayLoaded = async (): Promise<void> => {
    if ((window as any).Razorpay) return;
    await new Promise<void>((resolve, reject) => {
      const existing = document.querySelector<HTMLScriptElement>(
        'script[src="https://checkout.razorpay.com/v1/checkout.js"]',
      );
      if (existing) {
        if ((window as any).Razorpay) return resolve();
        existing.addEventListener("load", () => resolve());
        existing.addEventListener("error", () =>
          reject(new Error("Failed to load Razorpay SDK")),
        );
        return;
      }
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("Failed to load Razorpay SDK"));
      document.body.appendChild(script);
    });
    // Race guard: onload can fire before the global is actually attached
    // in some browsers/adblock scenarios.
    if (!(window as any).Razorpay) {
      throw new Error(
        "Razorpay SDK did not initialize. Please disable ad-blockers and retry.",
      );
    }
  };

  const runRazorpay = async () => {
    if (isDirectCheckout && !directCourse) return;
    const cartCourseIds = items.map((item) => item.courseId);
    const target = isDirectCheckout
      ? {
          course_id: directCourse.course_id,
          coupon_code: trimmedCode || undefined,
        }
      : {
          course_ids: cartCourseIds,
          coupon_code: appliedCoupon?.code || undefined,
        };
    track(
      "checkout_start",
      isDirectCheckout ? directCourse.course_id : cartCourseIds[0],
    ); // R1 funnel
    const orderResp = await api.post("/payments/create-order", target);
    const orderData = orderResp.data;

    await ensureRazorpayLoaded();

    const options: any = {
      key: orderData.key_id,
      amount: orderData.amount,
      currency: orderData.currency || "INR",
      name: "SashaInfinity LMS",
      description: isDirectCheckout
        ? directCourse.title
        : `${cartCourseIds.length} course${cartCourseIds.length === 1 ? "" : "s"}`,
      order_id: orderData.order_id,
      handler: async (paymentResponse: any) => {
        try {
          await api.post("/payments/verify", {
            razorpay_order_id: paymentResponse.razorpay_order_id,
            razorpay_payment_id: paymentResponse.razorpay_payment_id,
            razorpay_signature: paymentResponse.razorpay_signature,
            ...(isDirectCheckout
              ? { course_id: directCourse.course_id }
              : { course_ids: cartCourseIds }),
          });
          // Only flip orderComplete AFTER verified server-side success.
          if (!isDirectCheckout) clearCart();
          setRedeemedViaCode(false);
          setOrderComplete(true);
          toast.success(
            isDirectCheckout
              ? "Payment successful! You are now enrolled."
              : "Payment successful! Your courses are now unlocked.",
          );
        } catch (verifyErr: any) {
          console.error("Payment verification failed:", verifyErr);
          const msg =
            verifyErr?.response?.data?.detail ||
            verifyErr?.response?.data?.message ||
            "Payment verification failed. Please contact support.";
          toast.error(msg);
        } finally {
          setProcessing(false);
        }
      },
      prefill: {
        name: user
          ? `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim()
          : "",
        email: user?.user_email ?? "",
      },
      theme: { color: "#f97316" },
      // R7: Indian checkout order — UPI first, then EMI / pay later, then cards & net banking
      config: {
        display: {
          blocks: {
            upi: { name: "Pay with UPI", instruments: [{ method: "upi" }] },
            emi: {
              name: "EMI & Pay Later",
              instruments: [
                { method: "emi" },
                { method: "paylater" },
                { method: "cardless_emi" },
              ],
            },
            other: {
              name: "Cards, net banking & wallets",
              instruments: [
                { method: "card" },
                { method: "netbanking" },
                { method: "wallet" },
              ],
            },
          },
          sequence: ["block.upi", "block.emi", "block.other"],
          preferences: { show_default_blocks: true },
        },
      },
      modal: {
        ondismiss: () => {
          toast.error("Payment cancelled");
          setProcessing(false);
        },
      },
    };

    const rzp = new (window as any).Razorpay(options);
    rzp.on("payment.failed", (resp: any) => {
      console.error("Razorpay payment.failed:", resp);
      toast.error(resp?.error?.description || "Payment failed");
      setProcessing(false);
    });
    rzp.open();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setProcessing(true);

    try {
      // A zero-value cart is completed locally through /orders. Any amount
      // due uses the same signed Razorpay flow as direct course checkout.
      if (!isDirectCheckout) {
        if (total === 0) {
          const createdOrder = await cartCheckout();
          setOrderId(createdOrder.id);
          setRedeemedViaCode(false);
          setOrderComplete(true);
          toast.success("Order completed successfully!");
          setProcessing(false);
        } else {
          await runRazorpay();
        }
        return;
      }

      if (!directCourse) {
        setProcessing(false);
        return;
      }

      // Direct-checkout unified flow:
      //   1. If a code was entered, try /enroll first — backend's resolver
      //      handles voucher (free + redeem), discount-coupon (may 402),
      //      referral (may 402 on paid), invalid (400).
      //   2. On 402 requires_payment, fall through to the Razorpay path.
      //   3. Free courses with no code still go through /enroll (same call).
      if (trimmedCode || directCourse.is_free) {
        try {
          await api.post(`/courses/${directCourse.course_id}/enroll`, {
            coupon_code: trimmedCode || undefined,
          });
          // Success — voucher redeemed OR free enrollment completed.
          setRedeemedViaCode(Boolean(trimmedCode));
          setOrderComplete(true);
          toast.success(
            trimmedCode
              ? "Code redeemed! You are now enrolled."
              : "Enrollment successful!",
          );
          setProcessing(false);
          return;
        } catch (err: any) {
          const status = err?.response?.status;
          if (status === 402) {
            // Expected: paid course + discount/referral coupon → need payment.
            // Fall through to Razorpay below.
          } else if (status === 400) {
            const detail =
              err?.response?.data?.detail ||
              err?.response?.data?.message ||
              "Invalid code";
            toast.error(detail);
            setProcessing(false);
            return;
          } else {
            throw err;
          }
        }
      }

      // Razorpay path — direct paid course without code, or post-402 fall-through.
      await runRazorpay();
      // Return early — success/failure is driven by Razorpay callbacks.
      return;
    } catch (error: any) {
      console.error("Checkout error:", error);
      const message =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        (error instanceof Error
          ? error.message
          : "Failed to process order. Please try again.");
      toast.error(message);
      setProcessing(false);
    }
  };

  // Derive the post-checkout redirect target without putting it in state —
  // state + setState-inside-effect caused a render loop on the previous fix.
  // CRITICAL: Use URL param courseId directly, not directCourse.state, to ensure
  // redirect matches the actual purchased course.
  const redirectPath =
    isDirectCheckout && courseId ? `/courses/${courseId}/learn` : "/my-courses";

  // Success-page countdown effect — kept at top level and gated on
  // orderComplete inside so the hook is always called in the same order.
  useEffect(() => {
    if (!orderComplete) return;

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          navigate(redirectPath);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [orderComplete, navigate, redirectPath]);

  if (orderComplete) {
    const successTitle = redeemedViaCode
      ? "Voucher Redeemed!"
      : isDirectCheckout
        ? "Enrollment Successful!"
        : "Order Complete!";
    const successBody = redeemedViaCode
      ? `Enrolled via voucher — you now have access to ${directCourse?.title ?? "the course"}.`
      : isDirectCheckout
        ? "You have been enrolled in the course. Start learning now!"
        : "Thank you for your purchase. You now have access to your courses.";

    return (
      <div className="min-h-screen si-hero py-8">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
          <Card tier="work" className="p-8 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <Check className="h-8 w-8 text-green-600" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-4">
              {successTitle}
            </h1>
            <p className="text-gray-600 mb-6">{successBody}</p>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
              <p className="text-blue-800 font-medium">
                Redirecting in {countdown} second{countdown !== 1 ? "s" : ""}...
              </p>
            </div>
            <div className="space-y-3">
              <Link to={redirectPath}>
                <Button className="w-full">Go to Course Now</Button>
              </Link>
              <Link to="/my-courses">
                <Button variant="outline" className="w-full">
                  View All My Courses
                </Button>
              </Link>
              {!isDirectCheckout && (
                <Link to="/courses">
                  <Button variant="outline" className="w-full">
                    Continue Shopping
                  </Button>
                </Link>
              )}
            </div>
            {user?.user_email && (
              <p className="text-sm text-gray-500 mt-4">
                A confirmation email has been sent to {user.user_email}
              </p>
            )}
          </Card>
        </div>
      </div>
    );
  }

  // Show loading state for direct checkout
  if (isDirectCheckout && loadingCourse) {
    return (
      <div className="min-h-screen si-hero flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading course information...</p>
        </div>
      </div>
    );
  }

  // Redirect if already enrolled in direct checkout course
  if (isDirectCheckout && directCourse?.is_enrolled) {
    return (
      <div className="min-h-screen si-hero flex items-center justify-center">
        <Card tier="work" className="p-8 text-center max-w-md">
          <Check className="h-16 w-16 text-green-600 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            Already Enrolled
          </h2>
          <p className="text-gray-600 mb-6">
            You are already enrolled in this course.
          </p>
          <Link to={`/courses/${directCourse.course_id}/learn`}>
            <Button className="w-full">Continue Learning</Button>
          </Link>
        </Card>
      </div>
    );
  }

  // Derive primary CTA label.
  const isFree = isDirectCheckout && directCourse?.is_free;
  const isZeroTotal = total === 0;
  const ctaLabel = looksLikeVoucher
    ? "Redeem Voucher"
    : isZeroTotal
      ? "Enroll for Free"
      : isFree
        ? "Complete Enrollment"
        : isDirectCheckout
          ? `Proceed to Pay ₹${total.toFixed(2)}`
          : `Proceed to Pay ₹${total.toFixed(2)}`;

  return (
    <div className="min-h-screen si-hero py-8">
      <PageLayout
        header={
          <PageHeader>
            {isDirectCheckout ? (
              <Link
                to={`/courses/${courseId}`}
                className="flex items-center text-blue-600 hover:text-blue-700 mr-4"
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back to Course
              </Link>
            ) : (
              <Link
                to="/cart"
                className="flex items-center text-blue-600 hover:text-blue-700 mr-4"
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back to Cart
              </Link>
            )}
            <h1 className="text-3xl font-bold text-gray-900">
              {isDirectCheckout ? "Enroll in Course" : "Checkout"}
            </h1>
          </PageHeader>
        }
        className="rd-screen rd-screen-checkout"
      >
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left column — code entry + CTA */}
          <div>
            <form onSubmit={handleSubmit} className="space-y-6">
              {isDirectCheckout && (
                <Card tier="work" className="p-6">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">
                    Referral / Coupon / Voucher
                  </h2>
                  <div>
                    <label
                      htmlFor="couponCode"
                      className="block text-sm font-medium text-gray-700 mb-1"
                    >
                      Code (Optional)
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        id="couponCode"
                        name="couponCode"
                        value={couponCode}
                        onChange={(e) => setCouponCode(e.target.value)}
                        placeholder="Enter referral, coupon, or voucher code"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        disabled={!!validatedCoupon}
                      />
                      {validatedCoupon ? (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={handleRemoveCoupon}
                          className="px-3"
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      ) : (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={handleValidateCoupon}
                          disabled={!trimmedCode || validatingCoupon}
                          className="px-4"
                        >
                          {validatingCoupon ? "Checking..." : "Apply"}
                        </Button>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      Vouchers (INTR-XXXX) enroll you for free. Referral and
                      discount coupon codes are validated automatically at
                      checkout.
                    </p>
                    {validatedCoupon && (
                      <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
                        ✓ {validatedCoupon.message}
                        {(validatedCoupon.discount_amount ?? 0) > 0 && (
                          <span className="ml-2 font-medium">
                            (Save ₹
                            {(validatedCoupon.discount_amount ?? 0).toFixed(2)})
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </Card>
              )}

              <Card tier="work" className="p-6">
                <p className="text-sm text-gray-600 mb-4 flex items-center">
                  <Lock className="h-4 w-4 mr-2" />
                  Payments are processed securely by Razorpay. Card details
                  are entered inside the Razorpay window — never on this page.
                </p>
                <Button
                  type="submit"
                  className="w-full"
                  size="lg"
                  disabled={processing}
                >
                  {processing ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Processing...
                    </>
                  ) : (
                    <>
                      <Lock className="h-4 w-4 mr-2" />
                      {ctaLabel}
                    </>
                  )}
                </Button>
              </Card>
            </form>
          </div>

          {/* Order Summary */}
          <div>
            <Card tier="work" className="p-6 sticky top-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                {isDirectCheckout ? "Course Summary" : "Order Summary"}
              </h2>

              <div className="space-y-4 mb-6">
                {isDirectCheckout && directCourse ? (
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h4 className="font-medium text-gray-900 text-sm">
                        {directCourse.title}
                      </h4>
                      <p className="text-sm text-gray-600">
                        By {directCourse.instructor?.name || "Instructor"}
                      </p>
                      <div className="flex gap-2 mt-2">
                        <span className="text-xs bg-gray-100 px-2 py-1 rounded">
                          {directCourse.level}
                        </span>
                        <span className="text-xs bg-gray-100 px-2 py-1 rounded">
                          {directCourse.duration}
                        </span>
                      </div>
                    </div>
                    <div className="text-right ml-4">
                      <span className="font-medium text-lg">
                        {directCourse.is_free
                          ? "Free"
                          : `₹${directCourse.sale_price || directCourse.price}`}
                      </span>
                      {directCourse.sale_price && (
                        <div className="text-sm text-gray-500 line-through">
                          ₹{directCourse.price}
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  items.map((item) => {
                    const displayPrice = item.salePrice ?? item.price;
                    return (
                      <div
                        key={item.courseId}
                        className="flex justify-between items-start"
                      >
                        <div className="flex-1">
                          <h4 className="font-medium text-gray-900 text-sm">
                            {item.title}
                          </h4>
                          <p className="text-sm text-gray-600">
                            By {item.instructor}
                          </p>
                        </div>
                        <div className="text-right ml-4">
                          <span className="font-medium">₹{displayPrice}</span>
                          {item.salePrice && (
                            <div className="text-sm text-gray-500 line-through">
                              ₹{item.price}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              <div className="border-t pt-4 space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Subtotal:</span>
                  <span>₹{basePrice.toFixed(2)}</span>
                </div>
                {isDirectCheckout &&
                  validatedCoupon &&
                  (validatedCoupon.discount_amount ?? 0) > 0 && (
                    <div className="flex justify-between text-green-600">
                      <span>
                        Discount (
                        {validatedCoupon.discount_type === "percentage"
                          ? `${validatedCoupon.discount_value}%`
                          : `₹${validatedCoupon.discount_value}`}
                        ):
                      </span>
                      <span>-₹{directCouponDiscount.toFixed(2)}</span>
                    </div>
                  )}
                {isDirectCheckout && trimmedCode && !validatedCoupon && (
                  <div className="flex justify-between text-amber-600">
                    <span>Code ({trimmedCode}):</span>
                    <span>Will be applied at checkout</span>
                  </div>
                )}
                {!isDirectCheckout && appliedCoupon && (
                  <div className="flex justify-between text-green-600">
                    <span>Coupon ({appliedCoupon.code}):</span>
                    <span>-₹{couponDiscount.toFixed(2)}</span>
                  </div>
                )}
                {tax > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Tax:</span>
                    <span>₹{tax.toFixed(2)}</span>
                  </div>
                )}
                <div className="flex justify-between text-lg font-bold pt-2 border-t">
                  <span>Total:</span>
                  <span>₹{total.toFixed(2)}</span>
                </div>
                {total === 0 && validatedCoupon && (
                  <div className="text-center text-green-600 font-medium text-sm">
                    <AstraSymbol value="🎉" /> Free with coupon!
                  </div>
                )}
              </div>

              <div className="mt-6 pt-6 border-t">
                <div className="flex items-center text-sm text-gray-600 mb-2">
                  <Lock className="h-4 w-4 mr-2" />
                  <span>Secure payments via Razorpay</span>
                </div>
                <p className="text-sm text-gray-600 mb-2">
                  ✓ 30-day money-back guarantee
                </p>
                <p className="text-sm text-gray-600">
                  ✓ Lifetime access to courses
                </p>
              </div>
            </Card>
          </div>
        </div>
      </PageLayout>
    </div>
  );
}
