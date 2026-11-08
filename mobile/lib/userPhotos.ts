import * as ImagePicker from 'expo-image-picker';

/** Kamera ya da galeriden bir yemek fotoğrafı seç (4:5 kırpma). Yükleme/onay sunucuda: api.uploadRecipePhoto */
const OPTS: ImagePicker.ImagePickerOptions = { mediaTypes: ['images'], allowsEditing: true, aspect: [4, 5], quality: 0.8 };

export async function pickPhoto(from: 'camera' | 'library'): Promise<{ uri: string } | 'cancel' | 'denied'> {
  if (from === 'camera') {
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) return 'denied';
  }
  const res = from === 'camera' ? await ImagePicker.launchCameraAsync(OPTS) : await ImagePicker.launchImageLibraryAsync(OPTS);
  return res.canceled || !res.assets[0] ? 'cancel' : { uri: res.assets[0].uri };
}
