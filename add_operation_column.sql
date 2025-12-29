-- Migration to add operation_type column to question_log table
-- Run this in Supabase SQL Editor if you are using PostgreSQL

ALTER TABLE question_log ADD COLUMN operation_type VARCHAR(20) DEFAULT 'multiply';
