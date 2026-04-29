import { FormattedMessage, FormattedRelativeTime } from "react-intl";
import { useEffect, useState, useCallback } from "react";
import { useNavigate, NavLink } from "react-router";

import SlButton from "@shoelace-style/shoelace/dist/react/button/index.js";
import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";

import ConfirmDialog from "../../components/ConfirmDialog/index.jsx";
import Header from "../header.jsx";
import Footer from "../footer.jsx";
import { useConfigContext } from "../../context/ConfigContext.jsx";
import { useAuth } from '../../context/AuthContext';

import '../../styles/maps.css';

export default function MapList() {
  const navigate = useNavigate();
  const { config } = useConfigContext();
  const { isAuthenticated } = useAuth();
  const [mapList, setMapList] = useState([]);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [confirmDialogData, setConfirmDialogData] = useState();

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

  const handleDeleteRequest = useCallback((map) => {
    setConfirmDialogData(map);
    setConfirmDialogOpen(true);
  });

  const handleDelete = useCallback(async (map) => {
    setMapList((list) => {
      return list.map((m) => {
        return {...m, ...{
          loading: map.id === m.id,
        }};
      });
    });

    const url = `${config.API_URL}/map/${map.id}`;
    const response = await fetch(url, {
      method: "DELETE",
      credentials: "include",
    });

    if (response.ok) {
      setMapList((list) => {
        return list.filter((m) => m.id !== map.id);
      });
    }
  }, []);

  return (
    <>
      <div className="app">
        <Header pageTitle={isAuthenticated ? "My Maps" : "Maps"} />

        <div className="mapscontent">
          <div className="mapscontent__header">
            <div className="mapscontent__header-left">
              <h1>
                {isAuthenticated ? <FormattedMessage id="app.navigation.mymaps" defaultMessage="My maps" /> :
                <FormattedMessage id="app.navigation.maps" defaultMessage="Maps" /> }
              </h1>
              <br />
              <h2><FormattedMessage id="app.maps.subtitle" defaultMessage="Create maps from chat conversations" /></h2>
            </div>
            <div className="mapscontent__header-right">
              <SlButton variant="primary" href="#/">
                <FormattedMessage id="app.maps.new" defaultMessage="Create new map" />
              </SlButton>

              { config.ENABLE_LIVE && <>
                <SlButton className="header__live-button" href="#linked" variant="default" outline>
                  <FormattedMessage id="app.navigation.live" defaultMessage="Live" />
                </SlButton>
              </>}
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
                  { isAuthenticated ?
                  <th>
                    <FormattedMessage id="app.maps.table.actions" defaultMessage="Actions" />
                  </th> : ""}
                </tr>
              </thead>

              <tbody>
                { mapList.map((map) => (<tr key={map.id}>
                  <td>
                    <div className="mapitem">
                      <div className="mapitem__icon">
                        <SlIcon name="file-earmark-fill" />
                      </div>
                      <NavLink to={"/map/" + map.id} className="mapitem__name">
                        <strong>{ map.name }</strong>
                        <small>
                          <FormattedMessage
                            id="app.maps.point_count"
                            defaultMessage="{count} points"
                            values={{count: map.count }}
                          />
                        </small>
                      </NavLink>
                    </div>
                  </td>
                  <td>
                    <strong>
                      <FormattedMessage id={"app.maps.sharing." + map.sharing} />
                    </strong> (<FormattedMessage id={"app.maps.sharing_explain." + map.sharing} />)
                  </td>
                  <td>
                    <strong>
                      <FormattedRelativeTime value={
                        ((new Date(map.updated_at)).getTime() - (new Date()).getTime()) / 1000
                      } unit="second" updateIntervalInSeconds={1} />
                    </strong>
                  </td>
                  { isAuthenticated ?
                  <td className="mapscontent__actions">
                    <SlButton outline loading={!!map.loading} onClick={() => handleDeleteRequest(map)}>
                      <SlIcon name="trash" slot="prefix" />
                    </SlButton>
                  </td>
                  : ""}
                </tr>)) }
              </tbody>
            </table>
          </div>
        </div>

        <Footer />
      </div>

      <ConfirmDialog
        open={confirmDialogOpen}
        setOpen={setConfirmDialogOpen}
        onConfirm={handleDelete}
        data={confirmDialogData}
        title={{id: "app.maps.confirmDelete.title", defaultMessage: "Delete this map?"}}
      >
        { confirmDialogData?.name }
      </ConfirmDialog>
    </>
  );
};
