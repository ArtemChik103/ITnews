import '@testing-library/jest-dom/vitest';

// jsdom stubs
HTMLElement.prototype.scrollIntoView = () => {};
HTMLCanvasElement.prototype.getContext = (() => null) as unknown as typeof HTMLCanvasElement.prototype.getContext;
