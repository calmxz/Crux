# Crux frontend

The Crux web client: a Vue 3 + Vite + PrimeVue + Pinia single-page app.
This is the previous, frozen version; see [`../README.md`](../README.md) for the project's status.

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Configure the backend API base URL

The client reads `VITE_API_BASE_URL` (default `http://localhost:8000/api`). Set it in
`frontend/.env.local` to point at a different backend.

### Compile and Minify for Production

```sh
npm run build
```

### Preview the Production Build

```sh
npm run preview
```

### Run Unit Tests with [Vitest](https://vitest.dev/)

```sh
npm run test:unit
```

### Run End-to-End Tests with [Playwright](https://playwright.dev/)

```sh
npm run test:e2e
```

### Lint with [ESLint](https://eslint.org/)

```sh
npm run lint
```

### Format with [Prettier](https://prettier.io/)

```sh
npm run format
```
