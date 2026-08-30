import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types';
import { apiClient } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('receiptrag_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchMe = async () => {
      if (token) {
        try {
          const res = await apiClient.get<User>('/auth/me');
          setUser(res.data);
        } catch (error) {
          console.error('Failed to fetch user:', error);
          setToken(null);
          localStorage.removeItem('receiptrag_token');
        }
      }
      setIsLoading(false);
    };
    fetchMe();
  }, [token]);

  const login = async (email: string, password: string) => {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);

    const res = await apiClient.post('/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    const newToken = res.data.access_token;
    localStorage.setItem('receiptrag_token', newToken);
    setToken(newToken);
    setUser(res.data.user);
  };

  const register = async (email: string, password: string, fullName?: string) => {
    const res = await apiClient.post('/auth/register', {
      email,
      password,
      full_name: fullName,
    });

    const newToken = res.data.access_token;
    localStorage.setItem('receiptrag_token', newToken);
    setToken(newToken);
    setUser(res.data.user);
  };

  const logout = () => {
    localStorage.removeItem('receiptrag_token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
