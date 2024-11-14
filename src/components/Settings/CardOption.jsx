import React from "react";

function CardOption({ img, title, children, selected, onClick, name }) {

  return (
    <div onClick={() => onClick(name)} className={["cardOption", selected ? "cardOptionSelected" : ""].join(" ")}>
        <img className="cardOptionImage" src={img} alt={title} />
        <h3>{title}</h3>
        {children}
    </div>

  );
}

export default CardOption;
