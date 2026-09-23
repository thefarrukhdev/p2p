export type SlotStatus = 'open' | 'booked' | 'in_progress' | 'completed' | 'cancelled' | 'absent';

export interface LoginRequest {
  login: string;
  password: string;
}

export interface LoginResponse {
  status: 'ok' | 'need_telegram';
  access_token?: string | null;
  refresh_token?: string | null;
  token_type?: string;
  onboarding_done: boolean;
  temp_token?: string | null;
  bot_url?: string | null;
}

export interface VerifyCodeRequest {
  temp_token: string;
  code: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  onboarding_done: boolean;
}

export interface UserPublic {
  id: string;
  school21_login: string;
  telegram_username?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  avatar_url?: string | null;
  campus?: string | null;
  core_program?: string | null;
  main_track?: string | null;
  coalition_name?: string | null;
  level: number;
  xp: number;
}

export interface UserMe extends UserPublic {
  email?: string | null;
  current_location?: string | null;
  peer_points: number;
  peer_coins: number;
  languages: string[];
  is_admin: boolean;
  onboarding_done: boolean;
}

export interface Slot {
  id: string;
  reviewer_id: string; // teacher
  reviewee_id?: string | null; // student (booker)
  reviewer_project: string;
  reviewee_project?: string | null;
  start_time: string;
  end_time: string;
  actual_start?: string | null;
  actual_end?: string | null;
  reviewer_started?: boolean;
  reviewee_started?: boolean;
  duration_minutes?: number | null;
  status: SlotStatus;
  is_online: boolean;
  campus: string;
  reviewer?: UserPublic;
  reviewee?: UserPublic;
}

export interface SlotCreate {
  reviewer_project: string;
  start_time: string;
  end_time: string;
  is_online: boolean;
}

export interface SlotSearchResult {
  id: string;
  start_time: string;
  end_time: string;
  campus: string;
  is_online: boolean;
}

export interface Review {
  id: string;
  slot_id: string;
  author_id: string;
  target_id: string;
  is_positive: boolean;
  comment?: string | null;
}

export interface ReviewCreate {
  slot_id: string;
  is_positive: boolean;
  comment?: string;
}

export interface Notification {
  id: string;
  type: string;
  title?: string | null;
  body?: string | null;
  slot_id?: string | null;
  is_read: boolean;
  created_at: string;
}

export interface DashboardResponse {
  user: UserMe;
  xp_to_next_level: number;
  active_slots: Slot[];
  unread_notifications: number;
}

export interface LeaderboardEntry {
  rank: number;
  user_id: string;
  first_name?: string | null;
  last_name?: string | null;
  value: number;
}

export interface OnboardingStatus {
  onboarding_done: boolean;
  main_track?: string | null;
  languages: string[];
}

export interface Project {
  id?: string;
  title: string;
}

export interface ProfileStats {
  positive_reviews: number;
  negative_reviews: number;
  all_reviews: number;
  taught_count: number;
  learned_count: number;
}
