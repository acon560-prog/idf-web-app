/**
 * Feedback open-access period switches.
 *
 * ON (current): hide home pricing; IDF works for any logged-in user (no payment).
 * OFF (restore paid mode):
 *   1) Set both flags below to restore UI (SHOW_PRICING=true, OPEN_ACCESS_MODE=false)
 *   2) Set OPEN_ACCESS_MODE=false in .github/workflows/deploy-cloud-run.yml
 *      (and redeploy) so the API enforces trials/subscriptions again.
 *
 * Does not delete Pricing.jsx or Stripe — only hides / bypasses temporarily.
 */
export const SHOW_PRICING = false;
export const OPEN_ACCESS_MODE = true;
