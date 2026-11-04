import { router } from 'expo-router';
import { useState } from 'react';

import ExportSuccessSheet from '@/components/ExportSuccessSheet';
import ListPicker from '@/components/ListPicker';
import { Button } from '@/components/ui';
import { api, MealPlanExport } from '@/lib/api';

/** Tek bir yemeğin malzemelerini seçilen (ya da yeni açılan) alışveriş listesine ekleyen düğme */
export default function AddRecipeToList({ recipeId, servings, kind }: {
  recipeId: number; servings?: number | null; kind?: 'primary' | 'secondary';
}) {
  const [picker, setPicker] = useState(false);
  const [result, setResult] = useState<MealPlanExport | null>(null);

  const add = async (listId: number) => {
    const out = await api.exportRecipe(recipeId, { list_id: listId, servings: servings ?? null });
    setPicker(false);
    setResult(out);
  };

  return (
    <>
      <Button title="Malzemeleri listeye ekle" kind={kind} onPress={() => setPicker(true)} />
      <ListPicker visible={picker} onClose={() => setPicker(false)} onPick={add} />
      <ExportSuccessSheet result={result} onClose={() => setResult(null)}
        onOpen={() => { const id = result!.list.id; setResult(null); router.push({ pathname: '/list/[id]', params: { id: String(id) } }); }} />
    </>
  );
}
