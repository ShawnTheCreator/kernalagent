
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

// Ensure environment variables are present before initializing
if (!supabaseUrl || !supabaseKey) {
    console.warn('Supabase credentials missing! Check .env.local');
}

export const supabase = createClient(supabaseUrl, supabaseKey);
