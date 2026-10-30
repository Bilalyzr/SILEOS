import { createContext, useContext } from "react";

/**
 * Lets fields tell the gateway shell when they gain or lose focus, so the
 * background network can brighten while the visitor is typing.
 */
export interface GatewayContextValue {
  reportFocus: (id: string, focused: boolean) => void;
}

export const GatewayContext = createContext<GatewayContextValue>({
  reportFocus: () => {},
});

export const useGateway = () => useContext(GatewayContext);
