/**
 * This is the save button in the home screen that only triggers a dialog that
 * actually does the saving
 */
import { FormattedMessage } from 'react-intl';

import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';
import SlIcon from '@shoelace-style/shoelace/dist/react/icon/index.js';

import { useConfigContext } from '../../context/ConfigContext';

export default function UpdateButton({
  mapData, data, dataFiles, onUpdate, setUploaded, loading, setLoading,
}) {
  const { config } = useConfigContext();

  async function handleClick() {
    const mediaFiles = data.features
      .filter(f => f.properties.file)
      .map(f => f.properties.file);
    const allFiles = Object.entries(dataFiles).filter(([filename, blob]) => {
      return mediaFiles.indexOf(filename) > -1;
    });

    try {
      // This has to happen before setLoading(true) because that call makes the
      // for disapear from the DOM, this returning an empty object.
      setLoading(true);
      setUploaded(0);

      for (let [filename, blob] of allFiles) {
        const formData = new FormData();
        formData.append("file", blob, filename);
        const mediaResponse = await fetch(`${config.API_URL}/map/media`, {
          method: "POST",
          credentials: "include",
          body: formData,
        });

        if (!mediaResponse.ok) {
          throw new Error(`Error saving media ${filename}`);
        }

        const newFilename = (await mediaResponse.json()).uri;

        data.features.forEach((feature) => {
          if (feature.properties.file === filename) {
            feature.properties.file = newFilename;
          }
        });

        setUploaded((prev) => prev + 1);
      }

      const response = await fetch(`${config.API_URL}/map/${mapData.id}/points/`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({...data, features: data.features.filter((f) => {
          return f._temporary;
        })}),
      });

      if (response.ok) {
        onUpdate();
        setLoading(false);
      } else {
        throw new Error("Your map contains errors that prevent it from saving");
      }
    } catch (e) {
      console.log(e.message);
      setLoading(false);
    }
  }

  return (
    <SlButton
      variant="default"
      outline
      loading={loading}
      size="small"
      onClick={handleClick}
    >
      <SlIcon slot="prefix" name="cloud-arrow-up-fill"></SlIcon>
      <FormattedMessage id="app.map.update" defaultMessage="Update" />
    </SlButton>
  );
}
