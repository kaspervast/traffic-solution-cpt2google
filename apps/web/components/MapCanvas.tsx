"use client";
import {useEffect,useRef} from "react";
import type {Segment} from "./types";
declare global{interface Window{google?:any}}

const congestion=(segment:Segment)=>{const ratio=(segment.current_speed_kph??segment.free_flow_speed_kph)/segment.free_flow_speed_kph;if(ratio>=.8)return{color:"#16a34a",label:"Free"};if(ratio>=.6)return{color:"#84cc16",label:"Moderate"};if(ratio>=.4)return{color:"#f59e0b",label:"Slow"};if(ratio>=.2)return{color:"#f97316",label:"Severe"};return{color:"#dc2626",label:"Gridlock"}};

export default function MapCanvas({segments,selected,onSelect,onRoadCreated,result,selectionMode}:{segments:Segment[];selected:string;onSelect:(id:string)=>void;onRoadCreated:(road:Segment)=>void;result:any;selectionMode:boolean}){
 const el=useRef<HTMLDivElement>(null),key=process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY;
 useEffect(()=>{if(!key||!el.current)return;let disposed=false;const timers:number[]=[];const init=()=>{if(disposed||!el.current)return;const g=window.google,map=new g.maps.Map(el.current,{center:{lat:22.294,lng:70.779},zoom:14,mapTypeControl:false,streetViewControl:false,clickableIcons:false});const directions=new g.maps.DirectionsService(),geocoder=new g.maps.Geocoder();
  const draw=(segment:Segment,path:any[])=>{const closed=result?.map_layer?.closed_segment_id===segment.id,diverted=result?.map_layer?.rerouted_segment_ids?.includes(segment.id),status=congestion(segment),color=closed?"#111827":diverted?"#7c3aed":status.color;const line=new g.maps.Polyline({map,path,strokeColor:color,strokeWeight:segment.id===selected?10:7,strokeOpacity:.88,zIndex:closed?8:segment.id===selected?6:3,icons:closed?[{icon:{path:"M 0,-2 0,2",strokeColor:"#ef4444",strokeWeight:4},offset:"0",repeat:"12px"}]:[{icon:{path:g.maps.SymbolPath.FORWARD_CLOSED_ARROW,scale:2.2,strokeColor:"#fff",fillColor:"#fff",fillOpacity:1},offset:"0%",repeat:"70px"}]});line.addListener("click",()=>onSelect(segment.id));if(!closed&&!window.matchMedia("(prefers-reduced-motion: reduce)").matches){let offset=Math.random()*100;timers.push(window.setInterval(()=>{offset=(offset+.7)%100;const icons=line.get("icons");if(icons?.[0]){icons[0].offset=`${offset}%`;line.set("icons",icons)}},80))}}
  segments.forEach(segment=>{const points=segment.geometry.map(([lng,lat])=>({lat,lng}));if(points.length<2)return;directions.route({origin:points[0],destination:points[points.length-1],travelMode:g.maps.TravelMode.DRIVING},(response:any,status:string)=>draw(segment,status==="OK"&&response?.routes?.[0]?.overview_path?response.routes[0].overview_path:points))});
  let first:any=null,markers:any[]=[];
  map.addListener("click",(event:any)=>{
    if(!selectionMode||!event.latLng)return;
    if(!first){first=event.latLng;markers.push(new g.maps.Marker({map,position:first,label:"A",title:"Road section start"}));return}
    const start=first,second=event.latLng;
    markers.push(new g.maps.Marker({map,position:second,label:"B",title:"Road section end"}));
    directions.route({origin:start,destination:second,travelMode:g.maps.TravelMode.DRIVING},(response:any,status:string)=>{
      const route=status==="OK"?response.routes[0]:null;
      const path=route?route.overview_path.map((point:any)=>[point.lng(),point.lat()]):[[start.lng(),start.lat()],[second.lng(),second.lat()]];
      const midpoint=route?.overview_path?.[Math.floor(route.overview_path.length/2)]||start;
      geocoder.geocode({location:midpoint},(results:any[])=>{
        const name=results?.[0]?.address_components?.find((component:any)=>component.types.includes("route"))?.long_name||results?.[0]?.formatted_address?.split(",")[0]||"Selected road section";
        onRoadCreated({id:`map_${start.lat().toFixed(5)}_${start.lng().toFixed(5)}_${second.lat().toFixed(5)}_${second.lng().toFixed(5)}`,name,direction:"selected section",geometry:path,lanes:1,free_flow_speed_kph:40,current_speed_kph:24,traffic_provenance:"estimated",mapping_confidence:route?.overview_path?.length ? .8 : .55,provenance:"derived",custom:true});
      });
    });
    first=null;
  });
 };if(window.google)init();else{const script=document.createElement("script");script.src=`https://maps.googleapis.com/maps/api/js?key=${key}&v=weekly`;script.async=true;script.onload=init;document.head.appendChild(script)}return()=>{disposed=true;timers.forEach(clearInterval)}},[key,segments,selected,onSelect,onRoadCreated,result,selectionMode]);return <div className={`map ${selectionMode?"selecting":""}`} ref={el} aria-label={selectionMode?"Click a start and end point to select a road section":"Animated congestion map"}/>;
}
