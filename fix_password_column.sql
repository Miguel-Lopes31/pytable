-- Run this SQL command in your Supabase SQL Editor
-- This will fix the password_hash column size issue

ALTER TABLE "user" ALTER COLUMN password_hash TYPE VARCHAR(255);
