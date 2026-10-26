export default function AlertsPage() {
  return (
    <main className="p-4">
      <h1 className="text-2xl font-bold mb-4">🔔 Alarmlar</h1>
      <div className="card p-6 text-center text-gray-500">
        <div className="text-3xl mb-2">🔕</div>
        <div className="text-sm">Henüz alarm yok</div>
        <div className="text-xs mt-1">Bir ürüne tıklayıp "fiyat düşünce bildir" deyin</div>
      </div>
    </main>
  );
}
