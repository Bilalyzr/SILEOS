import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Trash2,
  ShoppingCart,
  Star,
  AlertCircle,
  CheckCircle,
  Loader2,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useCart } from "@/contexts/CartContext";
import toast from "react-hot-toast";

export function CartPage() {
  const {
    items,
    removeFromCart,
    appliedCoupon,
    setAppliedCoupon,
    applyCoupon,
  } = useCart();
  const [couponCode, setCouponCode] = useState("");
  const [couponError, setCouponError] = useState<string | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  const subtotal = items.reduce((sum, item) => {
    const price = item.salePrice ?? item.price;
    return sum + price;
  }, 0);

  const savings = items.reduce(
    (sum, item) => sum + (item.salePrice ? item.price - item.salePrice : 0),
    0,
  );

  const couponDiscount = appliedCoupon ? appliedCoupon.discountAmount : 0;
  const total = Math.max(0, subtotal - couponDiscount);

  const validateCoupon = async () => {
    if (!couponCode.trim()) {
      setCouponError("Please enter a coupon code");
      return;
    }

    setIsValidating(true);
    setCouponError(null);

    try {
      await applyCoupon(couponCode);
      toast.success("Coupon applied successfully!");
      setCouponCode("");
      setCouponError(null);
    } catch (error: any) {
      // Prefer the server-provided `detail` (FastAPI HTTPException)
      // or axios response message when available.
      const serverMessage =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        (error instanceof Error ? error.message : "Failed to validate coupon");
      setCouponError(serverMessage);
      toast.error(serverMessage);
    } finally {
      setIsValidating(false);
    }
  };

  const removeCoupon = () => {
    setAppliedCoupon(null);
    setCouponCode("");
    setCouponError(null);
    toast.success("Coupon removed");
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <PageLayout
        header={
          <PageHeader>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Shopping Cart
            </h1>
            <p className="text-gray-600">
              {items.length} course{items.length !== 1 ? "s" : ""} in cart
            </p>
          </PageHeader>
        }
        className="rd-screen rd-screen-cart"
      >
        {items.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Cart Items */}
            <div className="lg:col-span-2 space-y-4">
              {items.map((item) => {
                const displayPrice = item.salePrice ?? item.price;
                const discount = item.salePrice
                  ? Math.round(
                      ((item.price - item.salePrice) / item.price) * 100,
                    )
                  : 0;

                return (
                  <Card tier="work" key={item.courseId} className="p-6">
                    <div className="flex gap-4">
                      <img
                        src={
                          item.thumbnail ||
                          "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=300&h=200&fit=crop"
                        }
                        alt={item.title}
                        className="w-32 h-20 object-cover rounded flex-shrink-0"
                      />

                      <div className="flex-1">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <h3 className="text-lg font-semibold text-gray-900 mb-1">
                              {item.title}
                            </h3>
                            <p className="text-sm text-gray-600 mb-2">
                              By {item.instructor}
                            </p>

                            <div className="flex items-center space-x-4 text-sm text-gray-600 mb-2">
                              {item.rating && (
                                <div className="flex items-center">
                                  <Star className="h-4 w-4 text-yellow-400 mr-1" />
                                  <span>{item.rating}</span>
                                </div>
                              )}
                              <Badge variant="outline" className="text-xs">
                                {item.level}
                              </Badge>
                            </div>
                          </div>

                          <div className="text-right">
                            <div className="flex items-center space-x-2 mb-2">
                              <span className="text-lg font-bold text-gray-900">
                                ₹{displayPrice}
                              </span>
                              {item.salePrice && (
                                <>
                                  <span className="text-sm text-gray-500 line-through">
                                    ₹{item.price}
                                  </span>
                                  {discount > 0 && (
                                    <Badge className="bg-green-600 text-xs">
                                      {discount}% off
                                    </Badge>
                                  )}
                                </>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-3">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => removeFromCart(item.courseId)}
                              className="text-red-600 hover:text-red-700"
                            >
                              <Trash2 className="h-4 w-4 mr-1" />
                              Remove
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>

            {/* Order Summary */}
            <div>
              <Card tier="work" className="p-6 sticky top-8">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  Order Summary
                </h2>

                <div className="space-y-3 mb-4">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Subtotal:</span>
                    <span className="font-medium">₹{subtotal.toFixed(2)}</span>
                  </div>

                  {savings > 0 && (
                    <div className="flex justify-between text-green-600">
                      <span>Savings:</span>
                      <span>-₹{savings.toFixed(2)}</span>
                    </div>
                  )}

                  {appliedCoupon && (
                    <div className="flex justify-between items-start text-green-600">
                      <div className="flex items-center space-x-1">
                        <CheckCircle className="h-4 w-4" />
                        <span>Coupon ({appliedCoupon.code}):</span>
                      </div>
                      <div className="text-right">
                        <div>-₹{couponDiscount.toFixed(2)}</div>
                        <button
                          onClick={removeCoupon}
                          className="text-xs text-red-600 hover:text-red-700 underline"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  )}

                  <hr className="my-3" />

                  <div className="flex justify-between text-lg font-bold">
                    <span>Total:</span>
                    <span>₹{total.toFixed(2)}</span>
                  </div>
                </div>

                {/* Coupon Code */}
                <div className="mb-6">
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      placeholder="Enter coupon code"
                      value={couponCode}
                      onChange={(e) => {
                        setCouponCode(e.target.value);
                        setCouponError(null);
                      }}
                      onKeyPress={(e) => {
                        if (e.key === "Enter") {
                          validateCoupon();
                        }
                      }}
                      disabled={!!appliedCoupon || isValidating}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed uppercase"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={validateCoupon}
                      disabled={
                        !!appliedCoupon || isValidating || !couponCode.trim()
                      }
                    >
                      {isValidating ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                          Validating...
                        </>
                      ) : (
                        "Apply"
                      )}
                    </Button>
                  </div>
                  {couponError && (
                    <div className="flex items-center space-x-1 text-red-600 text-sm mt-2">
                      <AlertCircle className="h-4 w-4" />
                      <span>{couponError}</span>
                    </div>
                  )}
                  {appliedCoupon && (
                    <div className="flex items-center space-x-1 text-green-600 text-sm mt-2">
                      <CheckCircle className="h-4 w-4" />
                      <span>
                        {appliedCoupon.discountType === "percentage"
                          ? `${appliedCoupon.discountValue}% discount applied!`
                          : `₹${appliedCoupon.discountValue} discount applied!`}
                      </span>
                    </div>
                  )}
                </div>

                <Link to="/checkout" className="block">
                  <Button className="w-full mb-4" size="lg">
                    Proceed to Checkout
                  </Button>
                </Link>

                <div className="text-center">
                  <p className="text-sm text-gray-600 mb-2">
                    30-Day Money-Back Guarantee
                  </p>
                  <p className="text-sm text-gray-600">Lifetime Access</p>
                </div>
              </Card>
            </div>
          </div>
        ) : (
          <div className="text-center py-12">
            <ShoppingCart className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-medium text-gray-900 mb-2">
              Your cart is empty
            </h3>
            <p className="text-gray-600 mb-6">
              Browse our courses and add them to your cart
            </p>
            <Link to="/courses">
              <Button size="lg">Browse Courses</Button>
            </Link>
          </div>
        )}
      </PageLayout>
    </div>
  );
}
