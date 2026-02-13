import { ScrollViewStyleReset } from 'expo-router/html';
import { type PropsWithChildren } from 'react';

// This file is web-only and used to configure the root HTML for every web page during static rendering.
// The contents of this function only run in Node.js environments and do not have access to the DOM or browser APIs.
export default function Root({ children }: PropsWithChildren) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
        
        {/* Ionicons font for @expo/vector-icons */}
        <link 
          href="https://unpkg.com/ionicons@7.1.0/dist/ionicons/ionicons.esm.js" 
          rel="modulepreload" 
        />
        <link 
          href="https://cdn.jsdelivr.net/npm/ionicons@7.1.0/dist/css/ionicons.min.css" 
          rel="stylesheet" 
        />
        
        {/* Icon font face definition */}
        <style dangerouslySetInnerHTML={{ __html: `
          @font-face {
            font-family: 'Ionicons';
            src: url('https://unpkg.com/ionicons@4.5.10-0/dist/fonts/ionicons.woff2') format('woff2'),
                 url('https://unpkg.com/ionicons@4.5.10-0/dist/fonts/ionicons.woff') format('woff'),
                 url('https://unpkg.com/ionicons@4.5.10-0/dist/fonts/ionicons.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
          }
          
          /* Ensure proper rendering */
          html, body, #root {
            width: 100%;
            height: 100%;
            margin: 0;
            padding: 0;
          }
        `}} />
        
        {/* Using the <ScrollViewStyleReset/> will reset the built-in body scroll behavior */}
        <ScrollViewStyleReset />
      </head>
      <body>{children}</body>
    </html>
  );
}
