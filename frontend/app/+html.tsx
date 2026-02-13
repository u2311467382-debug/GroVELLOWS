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
        
        {/* Icon font face definition - @expo/vector-icons uses 'ionicons' (lowercase) as font family */}
        <style dangerouslySetInnerHTML={{ __html: `
          @font-face {
            font-family: 'ionicons';
            src: url('https://cdn.jsdelivr.net/npm/@nickvdyck/react-native-vector-icons-web@4.0.0/fonts/Ionicons.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
            font-display: block;
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
