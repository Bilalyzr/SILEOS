/**
 * Client-side validation mirroring the server's `_validate_questions` (spec
 * R7, backend/app/routers/quizzes.py). Returns human-readable errors; []
 * means valid. The SERVER is authoritative — this only powers the builder's
 * inline hints and reduces round trips; it must never reject something the
 * server would accept, or vice versa silently accept something the server
 * 422s on.
 *
 * Mirrors these exact server rules:
 *   - type must be one of QUESTION_TYPES
 *   - points: integer 1..1000, required, for every type
 *   - multiple_choice / multi_select: >=2 non-empty (trimmed) options
 *     - multiple_choice: correctAnswer is an in-range integer index
 *     - multi_select: correctAnswers is a list of >=1 distinct, in-range
 *       integer indices
 *   - true_false: correctAnswer in {"true","false"}
 *   - fill_in_blank: correctAnswer non-empty (trimmed), <=200 chars
 *   - short_answer: correctAnswer optional (empty -> manual grade, R8)
 *   - essay/open_ended: no answer required
 */

export type QuizQuestionType =
  | 'multiple_choice'
  | 'multi_select'
  | 'true_false'
  | 'short_answer'
  | 'essay'
  | 'open_ended'
  | 'fill_in_blank';

export interface ValidatableQuestion {
  type: QuizQuestionType | string;
  question?: string;
  points?: number;
  options?: string[];
  correctAnswer?: string | number;
  correctAnswers?: number[];
  explanation?: string;
}

export const QUESTION_TYPES: readonly string[] = [
  'multiple_choice',
  'true_false',
  'short_answer',
  'essay',
  'open_ended',
  'fill_in_blank',
  'multi_select',
];

export const FILL_IN_BLANK_MAX_LEN = 200;

function isStrictInt(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value);
}

export interface QuestionValidationError {
  index: number;
  message: string;
}

/**
 * Validates one question. Returns an error message, or null if valid.
 * Deliberately does NOT check `question` text non-empty — the server's
 * `_validate_questions` doesn't enforce that either (question_title
 * defaults to "" and is accepted), so this stays a client-only UX nicety
 * handled separately by the caller rather than baked into the shared
 * server-mirroring helper.
 */
export function validateQuestion(q: ValidatableQuestion): string | null {
  if (!q || typeof q !== 'object') return 'question must be an object';

  if (!QUESTION_TYPES.includes(q.type)) {
    return `question type must be one of ${QUESTION_TYPES.join(', ')}`;
  }

  const points = q.points;
  if (points === undefined || points === null) {
    return 'points is required';
  }
  if (!isStrictInt(points) || points < 1 || points > 1000) {
    return 'points must be an integer between 1 and 1000';
  }

  if (q.type === 'multiple_choice' || q.type === 'multi_select') {
    const rawOptions = q.options;
    if (!Array.isArray(rawOptions)) {
      return 'options must be a list of at least 2 entries';
    }
    const trimmed: string[] = [];
    for (const option of rawOptions) {
      const text = typeof option === 'string' ? option.trim() : '';
      if (!text) return 'options must not be empty';
      trimmed.push(text);
    }
    if (trimmed.length < 2) {
      return 'at least 2 non-empty options are required';
    }

    if (q.type === 'multiple_choice') {
      const correctAnswer = q.correctAnswer;
      if (!isStrictInt(correctAnswer)) {
        return 'correctAnswer must be an integer option index';
      }
      if (correctAnswer < 0 || correctAnswer >= trimmed.length) {
        return 'correctAnswer must be a valid option index';
      }
    } else {
      const correctAnswers = q.correctAnswers;
      const valid =
        Array.isArray(correctAnswers) &&
        correctAnswers.length >= 1 &&
        correctAnswers.every((a) => isStrictInt(a)) &&
        correctAnswers.every((a) => a >= 0 && a < trimmed.length) &&
        new Set(correctAnswers).size === correctAnswers.length;
      if (!valid) {
        return 'correctAnswers must be a list of at least 1 distinct, in-range option index';
      }
    }
  } else if (q.type === 'true_false') {
    if (q.correctAnswer !== 'true' && q.correctAnswer !== 'false') {
      return 'correctAnswer must be "true" or "false"';
    }
  } else if (q.type === 'fill_in_blank') {
    const text = typeof q.correctAnswer === 'string' ? q.correctAnswer.trim() : '';
    if (!text) return 'correctAnswer must not be empty';
    if (text.length > FILL_IN_BLANK_MAX_LEN) {
      return `correctAnswer must be ${FILL_IN_BLANK_MAX_LEN} characters or fewer`;
    }
  }
  // short_answer: correctAnswer optional (empty -> manual grade, R8).
  // essay/open_ended: no answer required.

  return null;
}

/**
 * Validates an entire question list. Returns [] when valid, otherwise one
 * {index, message} per invalid question (in list order — NOT stopping at
 * the first, unlike the server, so the UI can highlight every offending
 * question at once).
 */
export function validateQuestions(questions: ValidatableQuestion[]): QuestionValidationError[] {
  if (!Array.isArray(questions)) return [{ index: 0, message: 'questions must be a list' }];
  const errors: QuestionValidationError[] = [];
  questions.forEach((q, index) => {
    const message = validateQuestion(q);
    if (message) errors.push({ index, message });
  });
  return errors;
}

/**
 * Non-blocking warning (deferred F6-style minor, Task 2 review): flags
 * questions where two options are identical after trim (case-sensitive —
 * the server doesn't dedupe case-insensitively, and multiple_choice/
 * multi_select correctness is index-based so an exact-string duplicate is
 * the only case actually ambiguous to a test-taker). Returns one message
 * per affected question; [] when no duplicates.
 */
export function duplicateOptionWarnings(questions: ValidatableQuestion[]): string[] {
  const warnings: string[] = [];
  questions.forEach((q, index) => {
    if (q.type !== 'multiple_choice' && q.type !== 'multi_select') return;
    const options = q.options;
    if (!Array.isArray(options)) return;
    const seen = new Set<string>();
    let hasDuplicate = false;
    for (const option of options) {
      const text = typeof option === 'string' ? option.trim() : '';
      if (!text) continue;
      if (seen.has(text)) {
        hasDuplicate = true;
        break;
      }
      seen.add(text);
    }
    if (hasDuplicate) {
      warnings.push(`Question ${index + 1} has duplicate options`);
    }
  });
  return warnings;
}

/** Maps a server 422 `{code, message, index}` detail to friendly copy for
 * the toast/inline error. Falls back to the server's own `message` for any
 * code not in this table (keeps new server codes non-fatal to the UI). */
const CODE_MESSAGES: Record<string, string> = {
  invalid_type: 'This question has an invalid type.',
  too_few_options: 'This question needs at least 2 non-empty options.',
  empty_option: 'Options cannot be empty.',
  correct_index_out_of_range: 'The selected correct answer is not a valid option.',
  correct_index_not_integer: 'Please select a correct answer for this question.',
  true_false_invalid: 'Please choose True or False for this question.',
  fill_in_blank_empty: 'Please enter the correct answer for this question.',
  fill_in_blank_too_long: `The answer must be ${FILL_IN_BLANK_MAX_LEN} characters or fewer.`,
  points_out_of_range: 'Points must be between 1 and 1000.',
  points_missing: 'Please enter a point value for this question.',
  multi_select_invalid: 'Please select at least one correct answer for this question.',
};

export interface ServerValidationDetail {
  code?: string;
  message?: string;
  index?: number;
}

export function friendlyServerError(detail: ServerValidationDetail | undefined | null): {
  message: string;
  index: number | null;
} {
  if (!detail || typeof detail !== 'object') {
    return { message: 'Failed to save quiz', index: null };
  }
  const code = detail.code;
  const index = typeof detail.index === 'number' ? detail.index : null;
  const message =
    (code && CODE_MESSAGES[code]) || detail.message || 'Failed to save quiz';
  return { message, index };
}
