import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';

export const useLectures = () => {
  const queryClient = useQueryClient();

  const lecturesQuery = useQuery({
    queryKey: ['lectures'],
    queryFn: async () => {
      const { data } = await api.get('/lectures/');
      return data;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      const { data } = await api.post('/lectures/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lectures'] });
    },
  });

  return {
    lectures: lecturesQuery.data,
    isLoading: lecturesQuery.isLoading,
    upload: uploadMutation,
  };
};
