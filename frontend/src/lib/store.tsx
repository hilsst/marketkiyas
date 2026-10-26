"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { SEED_LISTS, ShoppingList, ListItem } from "./demo-data";

const KEY = "mk_lists_v2"; 
const SAVINGS_KEY = "mk_savings_v1";

export interface SavingsRecord {
  id: string;
  date: string;
  amount: number;
  listName: string;
  itemCount: number;
}

interface Ctx {
  lists: ShoppingList[]; hydrated: boolean;
  savings: SavingsRecord[];
  createList: (name: string) => number;
  addItem: (listId: number, groupId: number, preferredProductId?: number | null) => void;
  updateItem: (listId: number, itemId: number, patch: Partial<ListItem>) => void;
  removeItem: (listId: number, itemId: number) => void;
  deleteList: (listId: number) => void;
  clearPreferences: (listId: number) => void;
  addSavings: (record: Omit<SavingsRecord, 'id'>) => void;
  toast: string | null; setToast: (s: string | null) => void;
}
const ListCtx = createContext<Ctx | null>(null);

export function ListProvider({ children }: { children: ReactNode }) {
  const [lists, setLists] = useState<ShoppingList[]>(SEED_LISTS);
  const [savings, setSavings] = useState<SavingsRecord[]>([]);
  const [hydrated, setHydrated] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    try { 
      const s = localStorage.getItem(KEY); 
      if (s) setLists(JSON.parse(s)); 
      const sv = localStorage.getItem(SAVINGS_KEY);
      if (sv) setSavings(JSON.parse(sv));
    } catch {}
    setHydrated(true);
  }, []);

  useEffect(() => { 
    if (hydrated) {
      localStorage.setItem(KEY, JSON.stringify(lists)); 
      localStorage.setItem(SAVINGS_KEY, JSON.stringify(savings));
    }
  }, [lists, savings, hydrated]);

  useEffect(() => {
    if (toast) { const t = setTimeout(() => setToast(null), 2200); return () => clearTimeout(t); }
  }, [toast]);

  const createList = (name: string) => {
    const id = Math.max(0, ...lists.map(l => l.id)) + 1;
    setLists(p => [...p, { id, name, items: [] }]);
    return id;
  };
  
  const addItem = (listId: number, groupId: number, preferredProductId: number | null = null) => {
    setLists(p => p.map(l => {
      if (l.id !== listId) return l;
      const ex = l.items.find(i => i.groupId === groupId);
      if (ex) {
        return { ...l, items: l.items.map(i => 
          i.id === ex.id ? { ...i, quantity: i.quantity + 1, preferredProductId: preferredProductId || i.preferredProductId } : i
        ) };
      }
      const nid = Math.max(0, ...l.items.map(i => i.id)) + 1;
      return { ...l, items: [...l.items, { id: nid, groupId, quantity: 1, isChecked: false, preferredProductId }] };
    }));
  };

  const updateItem = (listId: number, itemId: number, patch: Partial<ListItem>) =>
    setLists(p => p.map(l => l.id !== listId ? l : {
      ...l, items: l.items.map(i => i.id === itemId ? { ...i, ...patch } : i) }));
      
  const removeItem = (listId: number, itemId: number) =>
    setLists(p => p.map(l => l.id !== listId ? l : {
      ...l, items: l.items.filter(i => i.id !== itemId) }));

  const deleteList = (listId: number) =>
    setLists(p => p.filter(l => l.id !== listId));
      
  const clearPreferences = (listId: number) =>
    setLists(p => p.map(l => l.id !== listId ? l : {
      ...l, items: l.items.map(i => ({ ...i, preferredProductId: null }))
    }));

  const addSavings = (record: Omit<SavingsRecord, 'id'>) => {
    setSavings(prev => [{ id: Date.now().toString(), ...record }, ...prev]);
  };

  return (
    <ListCtx.Provider value={{ lists, hydrated, savings, createList, addItem, updateItem, removeItem, deleteList, clearPreferences, addSavings, toast, setToast }}>
      {children}
      {toast && (
        <div className="fixed bottom-20 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-sm px-4 py-2 rounded-full shadow-lg z-50">
          {toast}
        </div>
      )}
    </ListCtx.Provider>
  );
}
export function useLists() {
  const c = useContext(ListCtx);
  if (!c) throw new Error("useLists inside ListProvider");
  return c;
}
