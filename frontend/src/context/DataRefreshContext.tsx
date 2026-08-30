import React, { createContext, useContext, useState, useCallback } from 'react';

interface DataRefreshContextValue {
  refreshToken: number;
  notifyDataChanged: () => void;
}

const DataRefreshContext = createContext<DataRefreshContextValue | undefined>(undefined);

/**
 * A tiny app-wide "something changed" signal. Any screen that lists
 * receipts/analytics subscribes to `refreshToken` in a useEffect dependency
 * array; anything that creates/updates/deletes a receipt calls
 * `notifyDataChanged()` so every mounted screen refetches immediately,
 * without requiring a manual browser refresh.
 */
export const DataRefreshProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [refreshToken, setRefreshToken] = useState(0);

  const notifyDataChanged = useCallback(() => {
    setRefreshToken((t) => t + 1);
  }, []);

  return (
    <DataRefreshContext.Provider value={{ refreshToken, notifyDataChanged }}>
      {children}
    </DataRefreshContext.Provider>
  );
};

export const useDataRefresh = (): DataRefreshContextValue => {
  const ctx = useContext(DataRefreshContext);
  if (!ctx) {
    throw new Error('useDataRefresh must be used within a DataRefreshProvider');
  }
  return ctx;
};
