Welcome to the codebase for Coasts in Crisis: Caribbean Arts and Cultures after Hurricanes, a digital art exhibit showcasing pieces local artists created in the archipelagos during the 2017 hurricane season. 

This project extends and preserves the work scholars Charlotte Rogers and Caroline Whitcomb invested in organizing an art gathering in 2019 at the University of Virginia. The event united seven Caribbean artists to celebrate, display, and discuss the work they felt compelled to create even amidst destruction. Video recordings of event activities are [available on YouTube](https://www.youtube.com/@coastsincrisis9010).

Originally, this digital exhibit was developed using [Drupal](https://new.drupal.org/) 7, but the project was recreated by [@winnieepm](https://github.com/winnieepm) as a static site using the [11ty](https://www.11ty.dev/docs/plugins/image/) framework in response to sustainability and longevity concerns. 

You can still access digital snapshots of the original project through the Internet Archive's [Wayback Machine](https://web.archive.org/web/20240826215207/https://coastsincrisis.net/)

Learn more visiting the project [Wiki](https://github.com/Coasts-in-Crisis/coastsincrisis/wiki)

## Local development

Clone this repo and use `npm start` in a command line interface.


## Deployment

The site is deployed to GitHub Pages by the [deploy workflow](.github/workflows/deploy.yaml). Every push to `main` installs dependencies (`npm ci`), builds the site with `npm run build-ghpages`, and publishes the `_site/` folder.

- **Pages setting:** in the repository's Settings → Pages, make sure the source is set to "GitHub Actions". The workflow won't publish without it.
- **Local build:** `npm run build` builds without a prefix, for checking output locally.
