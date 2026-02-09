# Frontend Coding Standards

This document outlines the coding standards and patterns for the frontend of the Vectra project. It is based on the analysis of core components and models.

## 1. Directory Structure

- **`src/models/`**: TypeScript classes representing data entities.
- **`src/components/`**: Vue components.
- **`src/services/`**: API and business logic services.

## 2. Component Structure (Vue)

All components should use the `<script setup lang="ts">` syntax.

### Section Comments

Organize code using the following comment headers to improve readability:

```typescript
// --- DEFINITIONS ---
// Props, Models, Emits

// --- STATE ---
// Refs, Reactive variables, Hooks ($q)

// --- COMPUTED ---
// Computed properties

// --- WATCHERS ---
// Watchers

// --- FUNCTIONS ---
// Event handlers, Helper functions
```

### Props and Models

- Use `defineModel` for two-way data binding where possible.
- Use `defineProps` with literal type definitions.

Example:

```typescript
const data = defineModel<KnowledgeBase>("data", { required: true });

const props = defineProps<{
  connectorType: string;
  title?: string;
}>();
```

## 3. Internationalization (i18n)

- All user-facing text must be internationalized using `vue-i18n`.
- Do not use hardcoded strings in templates or scripts.
- Use the `$t('key')` function or `t('key')` from `useI18n` hook.
- Store translations in `src/i18n/en-US/index.ts` AND `src/i18n/fr/index.ts`. All text must be translated in both English (en-US) and French (fr).

Example:

```vue
<!-- BAD -->
<div>Hello World</div>

<!-- GOOD -->
<div>{{ $t('helloWorld') }}</div>
```

## 4. Notifications

- All notifications (success, error, warning, info) must use the `useNotification` composable.
- Do not use `Quasar`'s `$q.notify` directly unless absolutely necessary.
- This ensures consistent styling and behavior across the application.

```typescript
import { useNotification } from "src/composables/useNotification";

const { notifySuccess, notifyError } = useNotification();

notifySuccess("Operation successful");
notifyError("Something went wrong");
```

## 5. Dialogs

- For conformation dialogs (delete confirmation, action confirmation), use the `useDialog` composable.
- Do not use `Quasar`'s `$q.dialog` directly for standard confirmations.
- This ensures consistent styling (e.g. "destructive" actions are automatically styled).

```typescript
import { useDialog } from "src/composables/useDialog";

const { confirm } = useDialog();

confirm({
  title: t("confirmDelete"),
  message: t("areYouSure"),
  confirmLabel: t("delete"),
  confirmColor: "negative",
  onConfirm: () => {
    // Action to perform on confirmation
    deleteItem(item);
  },
});
```

## 5. Tooltips

- All tooltips must use the `AppTooltip` component instead of `q-tooltip`.
- Do not use `Quasar`'s `q-tooltip` directly.
- `AppTooltip` provides consistent defaults:
  - 500ms delay before showing
  - 10px vertical offset
  - Dark background (`bg-grey-9`) with readable text
- All `q-tooltip` props can be overridden via standard props.

```typescript
import AppTooltip from "components/common/AppTooltip.vue";

<q-btn icon="add">
  <AppTooltip>{{ $t('create') }}</AppTooltip>
</q-btn>

// Custom positioning
<q-btn>
  <AppTooltip anchor="top middle">Different position</AppTooltip>
</q-btn>
```

## 6. Data Model Parity

- **Mirroring Backend**: TypeScript classes/interfaces in `src/models/` must mirror their Pydantic counterparts exactly.
- **Enum Matching**: TypeScript Enums must match the Python Enums string-for-string.
- **No Mapping Magic**: Avoid complex mapping logic in the frontend. If the API data shape is awkward, fix the API, don't hack the Frontend.

## 7. Documentation

- **Code Documentation**: Code must be well documented. This is not optional.
  - **JSDoc/TSDoc**: All exported functions, classes, interfaces, and complex component props/methods must have descriptive JSDoc/TSDoc comments explaining their purpose, arguments/props, and return values/emits.
  - **Inline Comments**: Use comments to explain **why** complex logic exists, not just **what** it does.
  - **Self-documenting code**: Prioritize clear variable, function, and component names over excessive comments.

## 8. Dead Code & Cleanup

- **Remove Unused Code**: Do not leave commented-out code or unused functions/variables in the codebase. If it's not used, delete it. Git history preserves it if needed later.
- **Remove Unused Files**: Regularly audit and delete files that are no longer referenced or used by the application.
- **No Debug Components**: Do not commit temporary debug components or scripts. These should be deleted after use.
- **Cleanliness**: Keep the codebase clean and focused on the current implementation.

## 9. Error Handling & Internationalization

- **i18n Structure**:

  - Generate `src/i18n/fr/index.ts` and `src/i18n/en/index.ts`.
  - Create an `errors: { ... }` section mapping EVERY backend `ERROR_CODE` (SCREAMING_SNAKE_CASE) to a user-friendly message.

- **Global Interceptor (`src/boot/axios.ts`)**:

  - **Functional Errors (4xx)**:
    - **Notification**: `type: 'warning'` (Orange).
    - **Message**: Translated string -> `$t('errors.' + response.data.error_code)`.
  - **Technical Errors (5xx / Network)**:
    - **Notification**: `type: 'negative'` (Red).
    - **Message**: Raw Code + Error ID -> `"System Error [internal_server_error] - ID: 12345"`.
    - **NO Translation** for technical errors to aid debugging.
  - **Tracing**:
    - Ensure `X-Correlation-ID` header is inspected/logged if useful for debugging.
    - If the backend returns an error `id`, it corresponds to the correlation/error ID. Display it prominently in 5xx errors.

- **Component Responsibility**:
  - Rely on the Global Interceptor for notifications.
  - Only catch errors if specific cleanup logic is required (e.g., stopping a loading spinner).
