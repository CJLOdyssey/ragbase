import api from './instance';

export interface AdminUser {
  user_id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface AdminUserListResponse {
  users: AdminUser[];
  total: number;
}

export async function listAdminUsers(page?: number, search?: string): Promise<AdminUserListResponse> {
  const { data } = await api.get('/admin/users', { params: { page, search } });
  return data;
}

export async function updateUserRole(userId: string, role: string): Promise<void> {
  await api.put(`/admin/users/${userId}/role`, { role });
}

export async function updateUserStatus(userId: string, isActive: boolean): Promise<void> {
  await api.put(`/admin/users/${userId}/status`, { is_active: isActive });
}
