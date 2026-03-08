import { FormattedMessage, FormattedRelativeTime } from "react-intl";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router";

import SlButton from "@shoelace-style/shoelace/dist/react/button/index.js";
import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";

import Header from "../header.jsx";
import Footer from "../footer.jsx";

import { useConfigContext } from "../../context/ConfigContext.jsx";

import '../../styles/maps.css';

function MapView() {
  const navigate = useNavigate();
  const { config } = useConfigContext();
  const [mapList, setMapList] = useState([]);

  useEffect(() => {
    async function fetchData() {
      const url = `${config.API_URL}/map`;
      const response = await fetch(url, {
        method: 'GET',
        credentials: 'include',
      });
      if (!response.ok) {
        navigate("/");
      }
      const json = await response.json();

      setMapList(json);
    }
    fetchData();
  }, []);

  return (
    <>
      <div className="app">
        <Header
          showDownloadButton={false}
        />

        <div className="mapscontent">
          <div className="mapscontent__header">
            <div className="mapscontent__header-left">
              <h1><FormattedMessage id="app.navigation.maps" defaultMessage="Maps" /></h1>
              <h2><FormattedMessage id="app.maps.subtitle" defaultMessage="Create maps from chat conversations" /></h2>
            </div>
            <div className="mapscontent__header-right">
              <SlButton variant="primary">
                <FormattedMessage id="app.maps.new" defaultMessage="Create new map" />
              </SlButton>
            </div>
          </div>

          <div className="mapscontent__body">
            <table cellSpacing="0">
              <thead>
                <tr>
                  <th>
                    <FormattedMessage id="app.maps.table.name" defaultMessage="Name" />
                  </th>
                  <th>
                    <FormattedMessage id="app.maps.table.permission" defaultMessage="Who can see" />
                  </th>
                  <th>
                    <FormattedMessage id="app.maps.table.updated" defaultMessage="Updated" />
                  </th>
                  <th>
                    <FormattedMessage id="app.maps.table.actions" defaultMessage="Actions" />
                  </th>
                </tr>
              </thead>

              <tbody>
                { mapList.map((map) => (<tr key={map.id}>
                  <td>
                    <div className="mapitem">
                      <div className="mapitem__icon">
                        <SlIcon name="file-earmark-fill" />
                      </div>
                      <div className="mapitem__name">
                        <strong>{ map.name }</strong>
                        <small>
                          <FormattedMessage
                            id="app.maps.point_count"
                            defaultMessage="{count} points"
                            values={{count: map.count }}
                          />
                        </small>
                      </div>
                    </div>
                  </td>
                  <td>
                    <strong>
                      <FormattedMessage id={"app.maps.sharing." + map.sharing} />
                    </strong> (<FormattedMessage id={"app.maps.sharing_explain." + map.sharing} />)
                  </td>
                  <td>
                    <strong>
                      <FormattedRelativeTime value={0} updateIntervalInSeconds={60} />
                    </strong>
                  </td>
                  <td className="mapscontent__actions">
                    <SlButton outline>
                      <SlIcon name="link" slot="prefix" />
                    </SlButton>
                    <SlButton outline>
                      <SlIcon name="file-earmark-plus-fill" slot="prefix" />
                    </SlButton>
                    <SlButton outline>
                      <SlIcon name="trash" slot="prefix" />
                    </SlButton>
                  </td>
                </tr>)) }
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <Footer
        className="footer__floating"
      />
    </>
  );
}

export default MapView;
