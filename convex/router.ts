import { httpRouter } from "convex/server";
import { httpAction } from "./_generated/server";
import { api } from "./_generated/api";

const http = httpRouter();

// Generate upload URL endpoint
http.route({
  path: "/api/storage/generateUploadUrl",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    try {
      const uploadUrl = await ctx.storage.generateUploadUrl();
      
      return new Response(JSON.stringify({
        uploadUrl,
      }), {
        status: 200,
        headers: { 
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        }
      });

    } catch (error) {
      console.error('Generate upload URL error:', error);
      return new Response(JSON.stringify({
        status: 'error',
        message: error instanceof Error ? error.message : 'Failed to generate upload URL'
      }), {
        status: 500,
        headers: { 
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        }
      });
    }
  }),
});

// Handle CORS preflight requests for upload URL
http.route({
  path: "/api/storage/generateUploadUrl",
  method: "OPTIONS",
  handler: httpAction(async (ctx, request) => {
    return new Response(null, {
      status: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      }
    });
  }),
});

export default http;
