import React from 'react';
import logo from '../../assets/hot-logo.svg';

/*
  A boundary for errors, displaying a message and
  contact options for support.
*/

export default class ErrorBoundary extends React.Component {
    constructor(props) {
      super(props);
      this.state = { hasError: false, error: null, errorInfo: null };
    }
  
    static getDerivedStateFromError(error) {
      return { hasError: true, error: error };  
    }
        
    render() {
      if (this.state.hasError) {
        const errorMsg = `${this.state.error.fileName}(${this.state.error.lineNumber}): \n ${this.state.error.toString()} \n ${this.state.error.stack}`;
        const mailLink = `mailto:emilio.mariscal@hotosm.org?subject=ChatMap Error&body=Hi, something went wrong with chatmap: ${errorMsg}`
        return (
          <div className="errorMessage">
            <header className="header">
              <h1 className="title"><img src={logo} className="logo" alt="logo" /> ChatMap</h1>
            </header>
            <div>
              <h2>Oops! something went wrong 🫢</h2>
              <h3>Let us know of this error so we can fix it as soon as possible!</h3>
              <p>
                <strong className="highlighted">Please, send the detail below to <a href={mailLink}>emilio.mariscal@hotosm.org</a></strong>
                <br /><br />or create an issue in <a href="https://github.com/hotosm/chatmap/issues">github.com/hotosm/chatmap/issues</a>
              </p>
              <div className="buttons">
                <sl-button variant="default" href={"/"}>
                  Reload
                  <sl-icon name="arrow-clockwise" slot="prefix"></sl-icon>
                </sl-button>
                
                <sl-button variant="primary" href={mailLink}>
                    Send error report
                    <sl-icon name="envelope-plus" slot="prefix"></sl-icon>
                </sl-button>
              </div>
              <pre>
                <strong>Error:</strong> {errorMsg}
              </pre>
            </div>
          </div>
        );
      }
      return this.props.children; 
    }
}
