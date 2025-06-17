import React, { createContext, useContext, useState, useEffect } from 'react';

// Create the context
const PlatformContext = createContext();

// Custom hook to use the platform context
export const usePlatform = () => useContext(PlatformContext);

// Provider component
export const PlatformProvider = ({ children }) => {
  const [platform, setPlatform] = useState({
    isElectron: false,
    isWeb: true,
  });

  useEffect(() => {
    // Check if running in Electron
    const isElectron = window.electron !== undefined;
    
    setPlatform({
      isElectron,
      isWeb: !isElectron,
    });
  }, []);

  return (
    <PlatformContext.Provider value={platform}>
      {children}
    </PlatformContext.Provider>
  );
};
