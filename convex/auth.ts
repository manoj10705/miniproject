// Auth disabled for this supply chain optimization app
// No authentication required - direct access for all users

import { query } from "./_generated/server";

export const loggedInUser = query({
  handler: async (ctx) => {
    // Return null since no authentication is required
    return null;
  },
});
