-- SQL Script to delete all courses and related data
-- Run this in your PostgreSQL database

BEGIN;

-- Delete in order to respect foreign key constraints
DELETE FROM quiz_answers;
DELETE FROM quiz_attempts;
DELETE FROM quiz_questions;
DELETE FROM quizzes;
DELETE FROM enrollments;
DELETE FROM payments;
DELETE FROM order_items;
DELETE FROM orders;
DELETE FROM lessons;
DELETE FROM course_categories;
DELETE FROM course_tags;
DELETE FROM courses;

-- Reset sequences to start from 1
ALTER SEQUENCE courses_id_seq RESTART WITH 1;
ALTER SEQUENCE lessons_id_seq RESTART WITH 1;
ALTER SEQUENCE quizzes_id_seq RESTART WITH 1;
ALTER SEQUENCE quiz_questions_id_seq RESTART WITH 1;
ALTER SEQUENCE enrollments_id_seq RESTART WITH 1;
ALTER SEQUENCE orders_id_seq RESTART WITH 1;
ALTER SEQUENCE order_items_id_seq RESTART WITH 1;
ALTER SEQUENCE payments_id_seq RESTART WITH 1;

COMMIT;

-- Verify deletion
SELECT 'Courses remaining: ' || COUNT(*) FROM courses;
SELECT 'Lessons remaining: ' || COUNT(*) FROM lessons;
SELECT 'Enrollments remaining: ' || COUNT(*) FROM enrollments;
